// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Privacy-reduced authenticated problem-report controller for issue #349.

// Submit reports only through the additive v2 API envelope.
import { api } from './api.js';
// Render escaped preview labels and shell-level status messages.
import { safe, toast } from './ui.js';
// Read and repaint the governed locale-specific feedback dictionary.
import { getLocaleState, t } from './i18n.js';

// Retain normalized screenshot bytes only while one dialog draft remains open.
let attachments = [];
// Preserve one replay identity across retries of the same visible draft.
let actionKey = '';

// Identify a low-cardinality browser family without retaining the raw agent string.
function browserFamily() {
  // Read browser-owned text only for immediate classification.
  const source = navigator.userAgent || '';
  // Distinguish Edge before generic Chromium.
  if (/Edg\//.test(source)) return 'Edge';
  // Identify Firefox.
  if (/Firefox\//.test(source)) return 'Firefox';
  // Identify Chromium-family browsers.
  if (/Chrome\//.test(source)) return 'Chrome';
  // Identify Safari only after Chromium exclusion.
  if (/Safari\//.test(source)) return 'Safari';
  // Return the bounded fallback.
  return 'Other';
}

// Identify a low-cardinality operating-system family without persisting device strings.
function osFamily() {
  // Read platform and agent only for local classification.
  const source = `${navigator.platform || ''} ${navigator.userAgent || ''}`;
  // Match the reviewed families in stable order.
  if (/Windows/i.test(source)) return 'Windows';
  // Group Apple mobile devices under iOS.
  if (/iPhone|iPad|iPod/i.test(source)) return 'iOS';
  // Match Android before generic Linux.
  if (/Android/i.test(source)) return 'Android';
  // Match Apple desktop devices.
  if (/Mac/i.test(source)) return 'macOS';
  // Match remaining Linux devices.
  if (/Linux/i.test(source)) return 'Linux';
  // Return the bounded fallback.
  return 'Other';
}

// Compress one selected image through a metadata-free canvas.
async function normalizeImage(file) {
  // Reject unsupported types and unusually large local files before decode work.
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 12_000_000) throw new Error(t('feedback.error.imageType', {}, 'feedback'));
  // Decode real pixels rather than trusting the filename.
  const bitmap = await createImageBitmap(file);
  // Bound the longest edge while preserving aspect ratio.
  const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
  // Allocate a clean metadata-free canvas.
  const canvas = document.createElement('canvas');
  // Set at least one output pixel in each dimension.
  canvas.width = Math.max(1, Math.round(bitmap.width * scale));
  // Set the bounded output height.
  canvas.height = Math.max(1, Math.round(bitmap.height * scale));
  // Paint decoded pixels onto the clean canvas.
  canvas.getContext('2d', { alpha: false }).drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  // Release decoder resources immediately.
  bitmap.close();
  // Start at readable JPEG quality.
  let quality = 0.82;
  // Encode the clean canvas into request transport form.
  let data = canvas.toDataURL('image/jpeg', quality);
  // Reduce quality in bounded steps when needed.
  while (data.length > 260_000 && quality > 0.42) { quality -= 0.08; data = canvas.toDataURL('image/jpeg', quality); }
  // Reject evidence that remains above the server ceiling.
  if (data.length > 275_000) throw new Error(t('feedback.error.imageSize', {}, 'feedback'));
  // Return no original filename or path.
  return { data, preview: data };
}

// Render screenshot previews and accessible removal actions.
function renderPreviews() {
  // Read the persistent preview outlet.
  const outlet = document.getElementById('report-previews');
  // Stop safely when the dialog is absent.
  if (!outlet) return;
  // Render one compact preview per in-memory image.
  outlet.innerHTML = attachments.map((item, index) => `<figure class="report-preview"><img src="${item.preview}" alt="${safe(t('feedback.screenshotAlt', { number: index + 1 }, 'feedback'))}"><button type="button" data-remove-feedback-image="${index}">${safe(t('feedback.removeScreenshot', {}, 'feedback'))}</button></figure>`).join('');
  // Bind immutable list replacement to each removal control.
  outlet.querySelectorAll('[data-remove-feedback-image]').forEach(button => { button.onclick = () => { attachments = attachments.filter((_, index) => index !== Number(button.dataset.removeFeedbackImage)); renderPreviews(); }; });
}

// Render the current reporter's own report status list inside the dialog.
function renderReporterStatuses(reports) {
  // Read or create the status outlet after the diagnostic context copy.
  let outlet = document.getElementById('report-status-list');
  // Create the outlet lazily so existing static markup remains compatible.
  if (!outlet) {
    // Allocate one compact status section.
    outlet = document.createElement('section');
    // Set a stable id for translation and browser evidence.
    outlet.id = 'report-status-list';
    // Add a governed test hook for reporter-visible status.
    outlet.dataset.testid = 'feedback-reporter-status';
    // Set a live region so post-submit status changes are announced.
    outlet.setAttribute('aria-live', 'polite');
    // Insert before the submit status message.
    document.getElementById('report-message')?.before(outlet);
  }
  // Hide the section when the reporter has no durable reports yet.
  if (!Array.isArray(reports) || reports.length === 0) {
    // Render an empty but explanatory state.
    outlet.innerHTML = `<h3>${safe(t('feedback.myReports', {}, 'feedback'))}</h3><p class="muted">${safe(t('feedback.myReportsEmpty', {}, 'feedback'))}</p>`;
    // Return after the empty-state paint.
    return;
  }
  // Render newest statuses without screenshots or Admin-only notes.
  outlet.innerHTML = `<h3>${safe(t('feedback.myReports', {}, 'feedback'))}</h3><ul class="report-status-list">${reports.slice(0, 5).map(report => `<li><strong>${safe(report.reference)}</strong> <span>${safe(t(`feedback.status.${report.status}`, {}, 'feedback'))}</span><small>${safe(report.summary)}</small></li>`).join('')}</ul>`;
}


// Load the current reporter's own statuses, hiding failures behind the existing registered-user policy.
async function loadReporterReports() {
  // Start protected loading because older servers may not yet expose the status endpoint.
  try {
    // Fetch current-user report summaries without Admin evidence.
    const result = await api('/api/v2/me/feedback/reports');
    // Render summaries from the standard envelope.
    renderReporterStatuses(result.reports || []);
  // Ignore status-load failures because submission remains the primary dialog action.
  } catch (_) {
    // Render no persistent error for a status sidebar failure.
    renderReporterStatuses([]);
  }
}


// Add pasted, dropped, or selected image files to the current draft.
async function addFiles(files) {
  // Read the localized live status outlet.
  const message = document.getElementById('report-message');
  // Convert FileList-like input into a bounded list.
  const selected = Array.from(files || []);
  // Reject collections above the three-image ceiling.
  if (attachments.length + selected.length > 3) { message.textContent = t('feedback.error.imageCount', {}, 'feedback'); return; }
  // Normalize files serially to bound decoder memory.
  try {
    // Process each accepted file in visible order.
    for (const file of selected) attachments.push(await normalizeImage(file));
    // Clear stale errors after complete success.
    message.textContent = '';
    // Repaint previews.
    renderPreviews();
  // Convert local validation failures into translated status.
  } catch (error) {
    // Show only the bounded message.
    message.textContent = error.message || t('feedback.error.imageType', {}, 'feedback');
  }
}

// Translate static dialog controls without recreating form state.
export function localizeFeedback() {
  // Map element ids to feedback-domain keys.
  const text = { 'report-problem-btn': 'feedback.open', 'report-problem-eyebrow': 'feedback.eyebrow', 'report-problem-title': 'feedback.title', 'report-problem-privacy': 'feedback.privacy', 'report-category-label': 'feedback.category', 'report-impact-label': 'feedback.impact', 'report-summary-label': 'feedback.summary', 'report-actual-label': 'feedback.actual', 'report-expected-label': 'feedback.expected', 'report-screenshot-title': 'feedback.screenshotTitle', 'report-screenshot-help': 'feedback.screenshotHelp', 'report-context-title': 'feedback.contextTitle', 'report-context-copy': 'feedback.contextCopy', 'report-cancel': 'feedback.cancel', 'report-submit': 'feedback.submit' };
  // Apply translated text to present nodes.
  Object.entries(text).forEach(([id, key]) => { const node = document.getElementById(id); if (node) node.textContent = t(key, {}, 'feedback'); });
  // Localize the close control's accessible name.
  document.getElementById('report-problem-close')?.setAttribute('aria-label', t('feedback.close', {}, 'feedback'));
  // Localize fixed category options.
  ['bug', 'visual', 'gameplay', 'account', 'idea', 'other'].forEach(value => { const option = document.querySelector(`#report-category option[value="${value}"]`); if (option) option.textContent = t(`feedback.category.${value}`, {}, 'feedback'); });
  // Localize fixed impact options.
  ['blocked', 'difficult', 'minor'].forEach(value => { const option = document.querySelector(`#report-impact option[value="${value}"]`); if (option) option.textContent = t(`feedback.impact.${value}`, {}, 'feedback'); });
  // Repaint preview accessible names after locale changes.
  renderPreviews();
}

// Show the reporting affordance only for authenticated persistent users.
export function syncFeedbackReporter(user) {
  // Read the persistent shell button.
  const button = document.getElementById('report-problem-btn');
  // Stop safely when shell markup is unavailable.
  if (!button) return;
  // Detect a canonical non-guest identity from server-owned fields.
  const registered = Boolean(user?.user_id) && String(user?.identity_provider || '').toLowerCase() !== 'guest' && !(user?.roles || []).includes('guest');
  // Hide the affordance outside the approved authenticated scope.
  button.hidden = !registered;
}

// Reset and open a new report draft.
function openDialog() {
  // Read the native dialog.
  const dialog = document.getElementById('report-problem-dialog');
  // Reset player fields.
  document.getElementById('report-problem-form')?.reset();
  // Remove prior in-memory evidence.
  attachments = [];
  // Allocate one replay identity for this visible draft.
  actionKey = crypto.randomUUID().replaceAll('-', '');
  // Clear prior status.
  document.getElementById('report-message').textContent = '';
  // Render the empty preview list.
  renderPreviews();
  // Open with browser-owned focus containment.
  dialog?.showModal();
  // Load this registered reporter's current report statuses.
  void loadReporterReports();
  // Focus the first task control.
  document.getElementById('report-category')?.focus();
}

// Submit the current draft through the additive v2 endpoint.
async function submitReport(event) {
  // Keep native method=dialog from closing before API success.
  event.preventDefault();
  // Read the submit control.
  const submit = document.getElementById('report-submit');
  // Read the live status outlet.
  const message = document.getElementById('report-message');
  // Lock duplicate clicks during the idempotent request.
  submit.disabled = true;
  // Publish translated in-flight state.
  message.textContent = t('feedback.submitting', {}, 'feedback');
  // Preserve the existing draft identity across retry.
  actionKey ||= crypto.randomUUID().replaceAll('-', '');
  // Build only privacy-reduced diagnostic context.
  const context = { route: location.pathname, locale: getLocaleState().locale, viewport_width: window.innerWidth, viewport_height: window.innerHeight, browser_family: browserFamily(), os_family: osFamily(), reduced_motion: matchMedia('(prefers-reduced-motion: reduce)').matches };
  // Submit while retaining the draft after a failure.
  try {
    // Send validated fields and normalized evidence only.
    const result = await api('/api/v2/feedback/reports', { method: 'POST', body: { idempotency_key: actionKey, category: document.getElementById('report-category').value, impact: document.getElementById('report-impact').value, summary: document.getElementById('report-summary').value, actual: document.getElementById('report-actual').value, expected: document.getElementById('report-expected').value, attachments: attachments.map(item => ({ data: item.data })), context } });
    // Announce the stable reference.
    message.textContent = t('feedback.success', { reference: result.reference }, 'feedback');
    // Mirror success through the persistent shell toast.
    toast(t('feedback.success', { reference: result.reference }, 'feedback'), true);
    // Refresh the visible reporter-status list so the filed report can be tracked.
    await loadReporterReports();
    // Retire the action identity only after confirmed success.
    actionKey = '';
    // Close after the live region has time to announce.
    setTimeout(() => document.getElementById('report-problem-dialog')?.close(), 500);
  // Convert safe API errors into local status.
  } catch (error) {
    // Preserve draft and evidence while keeping every server failure behind localized public copy.
    message.textContent = t('feedback.error.submit', {}, 'feedback');
  // Always restore the submit control.
  } finally {
    // Re-enable the action after request settlement.
    submit.disabled = false;
  }
}

// Bind persistent dialog controls exactly once after i18n initialization.
export function bindFeedbackDialog() {
  // Open a clean draft from the shell affordance.
  document.getElementById('report-problem-btn').onclick = openDialog;
  // Define shared cancellation teardown.
  const close = () => { attachments = []; actionKey = ''; document.getElementById('report-problem-dialog')?.close(); };
  // Bind both close controls.
  document.getElementById('report-problem-close').onclick = close;
  // Bind explicit cancellation.
  document.getElementById('report-cancel').onclick = close;
  // Bind API submission.
  document.getElementById('report-problem-form').onsubmit = submitReport;
  // Open the hidden picker from the dropzone.
  document.getElementById('report-dropzone').onclick = () => document.getElementById('report-file-input').click();
  // Preserve keyboard activation semantics.
  document.getElementById('report-dropzone').onkeydown = event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); document.getElementById('report-file-input').click(); } };
  // Normalize picker files.
  document.getElementById('report-file-input').onchange = event => addFiles(event.target.files);
  // Expose drag state without accepting browser navigation.
  document.getElementById('report-dropzone').ondragover = event => { event.preventDefault(); event.currentTarget.classList.add('dragging'); };
  // Clear drag state on leave.
  document.getElementById('report-dropzone').ondragleave = event => event.currentTarget.classList.remove('dragging');
  // Normalize dropped files.
  document.getElementById('report-dropzone').ondrop = event => { event.preventDefault(); event.currentTarget.classList.remove('dragging'); addFiles(event.dataTransfer.files); };
  // Accept pasted image files only while the native dialog owns focus.
  document.getElementById('report-problem-dialog').onpaste = event => { const files = Array.from(event.clipboardData?.items || []).filter(item => item.kind === 'file').map(item => item.getAsFile()).filter(Boolean); if (files.length) { event.preventDefault(); addFiles(files); } };
  // Apply the current locale immediately.
  localizeFeedback();
}
