// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the privacy-bounded problem-report inbox and triage workspace. (ADMIN-025)

// Preserve governed filters within the lifetime of one Admin page.
const INITIAL_FILTERS = Object.freeze({
  priority: '',
  status: '',
  category: '',
  impact: '',
  locale: '',
  route: '',
  reporter: '',
  created_from: '',
  created_to: '',
});

// Build the interactive Feedback tab.
export function createFeedbackTab(dependencies) {
  // Capture the accepted API, locale, rendering, and notification seams.
  const {
    api, emptyState, getLocaleState, html, humanLabel, isActiveTab, option,
    post, safe, setTitle, t, table, toast, view,
  } = dependencies;
  // Retain filters across detail navigation, refreshes, and locale rerenders.
  let feedbackFilters = { ...INITIAL_FILTERS };

  // Render one governed select from a fixed value list.
  function feedbackSelect(id, values, selected, emptyLabel, keyPrefix = '') {
    // Build the optional all-values row only for filter controls.
    const emptyOption = emptyLabel ? html`<option value="">${safe(emptyLabel)}</option>` : '';
    // Return stable labels without an invalid empty choice in detail forms.
    const entries = values.map(value => option(
      value,
      keyPrefix ? t(`${keyPrefix}.${value}`, {}, 'feedback') : humanLabel(value),
      selected,
    ));
    return html`<select id="${safe(id)}">${emptyOption}${entries}</select>`;
  }

  // Allocate one strong replay key for each explicit Admin mutation.
  function feedbackActionKey() {
    // Remove separators so the key matches the shared service contract.
    return crypto.randomUUID().replaceAll('-', '');
  }

  // Render one labeled select filter.
  function selectFilter(labelKey, id, values, selected, keyPrefix = '') {
    // Localize the visible label and all-values row through the Feedback domain.
    const label = safe(t(labelKey, {}, 'feedback'));
    const all = t('feedback.admin.all', {}, 'feedback');
    return html`<label>${label}${feedbackSelect(id, values, selected, all, keyPrefix)}</label>`;
  }

  // Render one labeled text or date filter.
  function inputFilter(labelKey, id, value, attributes = '') {
    // Keep fixed reviewed attributes separate from escaped user-entered values.
    const label = safe(t(labelKey, {}, 'feedback'));
    return html`<label>${label}<input id="${safe(id)}" value="${safe(value)}"${attributes}></label>`;
  }

  // Render all governed inbox filters and actions.
  function inboxFilters(data) {
    // Preserve server-published filter enums with stable priority defaults.
    const selects = [
      selectFilter('feedback.admin.priority', 'feedback-priority-filter', data.priorities || ['P1', 'P2', 'P3'], feedbackFilters.priority),
      selectFilter('feedback.admin.status', 'feedback-status-filter', data.statuses || [], feedbackFilters.status, 'feedback.status'),
      selectFilter('feedback.admin.category', 'feedback-category-filter', data.categories || [], feedbackFilters.category, 'feedback.category'),
      selectFilter('feedback.admin.impact', 'feedback-impact-filter', data.impacts || [], feedbackFilters.impact, 'feedback.impact'),
      selectFilter(
        'feedback.admin.locale',
        'feedback-locale-filter',
        getLocaleState().locales.map(locale => locale.id),
        feedbackFilters.locale,
      ),
    ];
    // Preserve bounded route, reporter, and timestamp filters.
    const inputs = [
      inputFilter('feedback.admin.routeFilter', 'feedback-route-filter', feedbackFilters.route, html` maxlength="120"`),
      inputFilter(
        'feedback.admin.reporter',
        'feedback-reporter-filter',
        feedbackFilters.reporter,
        html` pattern="USR-[A-F0-9]{16}"`,
      ),
      inputFilter(
        'feedback.admin.createdFrom',
        'feedback-created-from-filter',
        feedbackFilters.created_from,
        html` type="datetime-local"`,
      ),
      inputFilter(
        'feedback.admin.createdTo',
        'feedback-created-to-filter',
        feedbackFilters.created_to,
        html` type="datetime-local"`,
      ),
    ];
    // Preserve explicit apply and retention actions.
    const apply = html`<button id="feedback-apply-filters" type="button">${safe(t('feedback.admin.apply', {}, 'feedback'))}</button>`;
    const cleanup = html`<button id="feedback-cleanup" type="button">${safe(t('feedback.admin.cleanup', {}, 'feedback'))}</button>`;
    return html`<div class="feedback-filters">${selects}${inputs}${apply}${cleanup}</div>`;
  }

  // Build one privacy-bounded inbox row.
  function reportRow(report) {
    // Preserve internal reference navigation without exposing attachment bytes.
    const reference = html`<button type="button" class="feedback-link" data-feedback-id="${safe(report.report_id)}">${safe(report.reference)}</button>`;
    const status = safe(t(`feedback.status.${report.status}`, {}, 'feedback'));
    const category = safe(t(`feedback.category.${report.category}`, {}, 'feedback'));
    const impact = safe(t(`feedback.impact.${report.impact}`, {}, 'feedback'));
    const priority = html`<span class="badge">${safe(report.priority)}</span>`;
    const values = [
      reference, priority, status, category, impact, report.reporter_reference,
      report.summary, report.route, report.created_at,
    ];
    // Preserve the exact nine-column row order.
    return html`<tr>${values.map(value => html`<td>${value}</td>`)}</tr>`;
  }

  // Render either the inbox table or its calm empty state.
  function inboxResults(rows) {
    // Return the accepted empty state when no report matches.
    if (!rows.length) {
      return emptyState(
        t('feedback.admin.emptyTitle', {}, 'feedback'),
        t('feedback.admin.emptyCopy', {}, 'feedback'),
        'admin-feedback-empty',
      );
    }
    // Preserve the complete nine-column inbox heading order.
    const heads = [
      'reference', 'priority', 'status', 'category', 'impact',
      'reporter', 'summary', 'route', 'created',
    ].map(key => t(`feedback.admin.${key}`, {}, 'feedback'));
    const label = safe(t('feedback.admin.tableLabel', {}, 'feedback'));
    return html`<div class="feedback-table-scroll" tabindex="0" role="region" aria-label="${label}">${table(heads, rows)}</div>`;
  }

  // Read all current filter control values after an explicit apply action.
  function readFilters() {
    // Preserve the exact request field names expected by the Admin API.
    feedbackFilters = Object.fromEntries(Object.keys(INITIAL_FILTERS).map((key) => {
      // Translate snake-case request names to their stable DOM control ids.
      const id = key === 'created_from' ? 'created-from' : key === 'created_to' ? 'created-to' : key;
      return [key, view.querySelector(`#feedback-${id}-filter`).value];
    }));
  }

  // Bind inbox refresh, cleanup, and detail navigation actions.
  function bindInboxActions() {
    // Apply selected filters through one canonical rerender.
    view.querySelector('#feedback-apply-filters').onclick = () => {
      // Capture the complete current filter set before loading.
      readFilters();
      // Refresh without losing the newly selected filters.
      feedbackReports();
    };
    // Resume interrupted deletions and enforce both retention ceilings.
    view.querySelector('#feedback-cleanup').onclick = async () => {
      // Run the protected cleanup route without publishing data externally.
      const result = await post('/api/v2/admin/feedback/cleanup', {});
      // Announce only the aggregate deleted-report count.
      toast(t('feedback.admin.cleaned', { reports: result.cleanup?.deleted || 0 }, 'feedback'), true);
      // Refresh the canonical inbox after cleanup.
      feedbackReports();
    };
    // Open details only through report identifiers returned by the server.
    view.querySelectorAll('[data-feedback-id]').forEach((button) => {
      // Bind each stable row identity to its detail route.
      button.onclick = () => feedbackDetail(button.dataset.feedbackId);
    });
  }

  // Load and render the attachment-free Admin problem-report inbox.
  async function feedbackReports() {
    // Set the tab heading through the localized Feedback domain.
    setTitle(t('feedback.admin.title', {}, 'feedback'), t('feedback.admin.subtitle', {}, 'feedback'));
    // Build a query containing only non-empty governed filters.
    const query = new URLSearchParams(Object.entries(feedbackFilters).filter(([, value]) => value));
    const suffix = query.toString() ? `?${query}` : '';
    // Fetch the additive v2 inbox contract.
    const data = await api(`/api/v2/admin/feedback/reports${suffix}`);
    // Stop a stale response from replacing a newer Admin tab.
    if (!isActiveTab('feedback')) return;
    // Render filters plus bounded result rows.
    const rows = (data.reports || []).map(reportRow);
    view.innerHTML = html`<section class="admin-card feedback-inbox" data-testid="admin-feedback-inbox">${inboxFilters(data)}${inboxResults(rows)}</section>`;
    // Bind explicit actions after the inbox markup is installed.
    bindInboxActions();
  }

  // Render one server-normalized evidence image.
  function evidenceFigure(attachment, index) {
    // Preserve metadata-free image bytes and bounded dimensions.
    const source = `data:${attachment.media_type};base64,${attachment.data}`;
    const alt = safe(t('feedback.screenshotAlt', { number: index + 1 }, 'feedback'));
    return html`<figure><img src="${safe(source)}" alt="${alt}"><figcaption>${safe(attachment.width)} × ${safe(attachment.height)} · ${safe(attachment.bytes)} bytes</figcaption></figure>`;
  }

  // Render immutable report prose and context.
  function reportContent(report) {
    // Preserve actual and expected prose as escaped server text.
    const actual = html`<h3>${safe(t('feedback.admin.actual', {}, 'feedback'))}</h3><p class="feedback-prose">${safe(report.actual)}</p>`;
    const expected = html`<h3>${safe(t('feedback.admin.expected', {}, 'feedback'))}</h3><p class="feedback-prose">${safe(report.expected)}</p>`;
    // Preserve allowlisted context values behind the shared table renderer.
    const rows = Object.entries(report.context || {}).map(([key, value]) => (
      html`<tr><td>${safe(humanLabel(key))}</td><td>${safe(value)}</td></tr>`
    ));
    const context = table([
      t('feedback.admin.field', {}, 'feedback'),
      t('feedback.admin.value', {}, 'feedback'),
    ], rows);
    return html`<section>${actual}${expected}<h3>${safe(t('feedback.admin.context', {}, 'feedback'))}</h3>${context}</section>`;
  }

  // Render controlled triage fields and manual GitHub linkage.
  function triageControls(report) {
    // Preserve fixed priority and workflow status choices.
    const priority = feedbackSelect('feedback-detail-priority', ['P1', 'P2', 'P3'], report.priority, '');
    const statuses = ['new', 'triaged', 'linked', 'resolved', 'duplicate', 'rejected'];
    const status = feedbackSelect('feedback-detail-status', statuses, report.status, '', 'feedback.status');
    // Preserve escaped internal notes and an explicit manual issue-link field.
    const notes = html`<label>${safe(t('feedback.admin.notes', {}, 'feedback'))}<textarea id="feedback-admin-notes" maxlength="4000" rows="7">${safe(report.admin_notes || '')}</textarea></label>`;
    const githubLabel = safe(t('feedback.admin.githubUrl', {}, 'feedback'));
    const githubValue = safe(report.github_issue_url || '');
    const githubInput = html`<input id="feedback-github-url" type="url" value="${githubValue}" placeholder="https://github.com/andreivorobiev/virtual-casino-simulator/issues/…">`;
    const github = html`<label>${githubLabel}${githubInput}</label>`;
    // Preserve all four explicit triage actions.
    const actions = ['save', 'prepareDraft', 'export', 'delete'].map((key) => {
      // Map translated keys to their established control identities.
      const id = key === 'prepareDraft' ? 'draft' : key;
      const style = key === 'save' ? html` class="gold"` : key === 'delete' ? html` class="danger"` : '';
      const label = safe(t(`feedback.admin.${key}`, {}, 'feedback'));
      return html`<button id="feedback-${id}"${style} type="button">${label}</button>`;
    });
    const priorityField = html`<label>${safe(t('feedback.admin.priority', {}, 'feedback'))}${priority}</label>`;
    const statusField = html`<label>${safe(t('feedback.admin.status', {}, 'feedback'))}${status}</label>`;
    const manual = html`<p class="muted">${safe(t('feedback.admin.manualOnly', {}, 'feedback'))}</p>`;
    return html`<section class="feedback-triage">${priorityField}${statusField}${notes}${github}${manual}${actions}</section>`;
  }

  // Render the complete detail surface before binding mutations.
  function renderDetail(report) {
    // Preserve reference, category, impact, and reporter badges.
    const badges = [
      report.reference,
      t(`feedback.category.${report.category}`, {}, 'feedback'),
      t(`feedback.impact.${report.impact}`, {}, 'feedback'),
      report.reporter_reference,
    ].map(value => html`<span class="badge">${safe(value)}</span>`);
    const back = html`<button id="feedback-back" type="button">${safe(t('feedback.admin.back', {}, 'feedback'))}</button>`;
    const evidence = (report.attachments || []).map(evidenceFigure);
    const noEvidence = html`<p class="muted">${safe(t('feedback.admin.noScreenshots', {}, 'feedback'))}</p>`;
    const heading = html`<div class="row">${back}${badges}</div><h2>${safe(report.summary)}</h2>`;
    const split = html`<div class="admin-split">${reportContent(report)}${triageControls(report)}</div>`;
    const evidenceHeading = html`<h3>${safe(t('feedback.admin.screenshots', {}, 'feedback'))}</h3>`;
    const evidenceView = html`<div class="feedback-evidence">${evidence.length ? evidence : noEvidence}</div>`;
    const draft = html`<div id="feedback-github-draft" class="feedback-draft" hidden></div>`;
    return html`<section class="admin-card feedback-detail" data-testid="admin-feedback-detail">${heading}${split}${evidenceHeading}${evidenceView}${draft}</section>`;
  }

  // Persist controlled triage fields and redraw from the server response.
  async function saveReport(reportId) {
    // Send only allowlisted triage fields with a strong caller-owned operation key.
    await api(`/api/v2/admin/feedback/reports/${encodeURIComponent(reportId)}`, {
      method: 'PATCH',
      body: {
        idempotency_key: feedbackActionKey(),
        priority: view.querySelector('#feedback-detail-priority').value,
        status: view.querySelector('#feedback-detail-status').value,
        admin_notes: view.querySelector('#feedback-admin-notes').value,
        github_issue_url: view.querySelector('#feedback-github-url').value,
      },
    });
    // Announce completion and refresh canonical detail.
    toast(t('feedback.admin.saved', {}, 'feedback'), true);
    feedbackDetail(reportId);
  }

  // Prepare and render a sanitized manual GitHub draft without publishing it.
  async function prepareDraft(reportId) {
    // Ask the local API to prepare only the reviewed title/body/label bundle.
    const prepared = await post(`/api/v2/admin/feedback/reports/${encodeURIComponent(reportId)}/github-draft`, {});
    const draft = prepared.draft || {};
    const outlet = view.querySelector('#feedback-github-draft');
    // Reveal and populate the local-only draft controls.
    outlet.hidden = false;
    const title = html`<label>${safe(t('feedback.admin.issueTitle', {}, 'feedback'))}<input id="feedback-draft-title" readonly value="${safe(draft.title || '')}"></label>`;
    const body = html`<label>${safe(t('feedback.admin.issueBody', {}, 'feedback'))}<textarea id="feedback-draft-body" readonly rows="14">${safe(draft.body || '')}</textarea></label>`;
    const labels = html`<p>${safe(t('feedback.admin.labels', {}, 'feedback'))}: ${safe((draft.labels || []).join(', '))}</p>`;
    const copy = html`<div class="row"><button id="feedback-copy-draft" type="button">${safe(t('feedback.admin.copyDraft', {}, 'feedback'))}</button></div>`;
    const heading = html`<h3>${safe(t('feedback.admin.draftTitle', {}, 'feedback'))}</h3>`;
    const manual = html`<p class="muted">${safe(t('feedback.admin.manualOnly', {}, 'feedback'))}</p>`;
    outlet.innerHTML = html`${heading}${manual}${title}${body}${labels}${copy}`;
    // Copy only after an explicit local Admin action.
    outlet.querySelector('#feedback-copy-draft').onclick = async () => {
      // Preserve the exact prepared title/body bundle.
      await navigator.clipboard.writeText(`${draft.title}\n\n${draft.body}`);
      toast(t('feedback.admin.copied', {}, 'feedback'), true);
    };
  }

  // Download only privacy-safe metadata after server evidence removal.
  async function exportReport(reportId, reference) {
    // Request the sanitized export envelope.
    const exported = await api(`/api/v2/admin/feedback/reports/${encodeURIComponent(reportId)}/export`);
    const blob = new Blob([JSON.stringify(exported.export || {}, null, 2)], { type: 'application/json' });
    // Trigger one ephemeral local download and revoke its object URL.
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${reference || 'feedback-report'}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
    toast(t('feedback.admin.exported', {}, 'feedback'), true);
  }

  // Require explicit confirmation before the recoverable privacy-deletion saga.
  async function deleteReport(reportId) {
    // Leave the report untouched when the operator cancels confirmation.
    if (!window.confirm(t('feedback.admin.deleteConfirm', {}, 'feedback'))) return;
    // Submit a strong caller-owned operation identity with the delete.
    await api(`/api/v2/admin/feedback/reports/${encodeURIComponent(reportId)}`, {
      method: 'DELETE',
      body: { idempotency_key: feedbackActionKey() },
    });
    // Announce completion before returning to the filtered inbox.
    toast(t('feedback.admin.deleted', {}, 'feedback'), true);
    feedbackReports();
  }

  // Bind detail navigation and all explicit triage actions.
  function bindDetailActions(reportId, report) {
    // Return to the filtered inbox without losing in-memory filter state.
    view.querySelector('#feedback-back').onclick = feedbackReports;
    // Bind each operation to the currently rendered canonical report.
    view.querySelector('#feedback-save').onclick = () => saveReport(reportId);
    view.querySelector('#feedback-draft').onclick = () => prepareDraft(reportId);
    view.querySelector('#feedback-export').onclick = () => exportReport(reportId, report.reference);
    view.querySelector('#feedback-delete').onclick = () => deleteReport(reportId);
  }

  // Render one canonical internal report with evidence and triage controls.
  async function feedbackDetail(reportId) {
    // Fetch the Admin-only detail contract.
    const data = await api(`/api/v2/admin/feedback/reports/${encodeURIComponent(reportId)}`);
    // Stop a stale response from replacing another selected tab.
    if (!isActiveTab('feedback')) return;
    // Read and render the canonical report object.
    const report = data.report || {};
    view.innerHTML = html`${renderDetail(report)}`;
    // Bind mutations only after the canonical detail is installed.
    bindDetailActions(reportId, report);
  }

  // Publish only the dispatcher-facing inbox renderer.
  return feedbackReports;
}
