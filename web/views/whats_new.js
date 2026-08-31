// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Present curated release copy without acquiring release, identity, or consent authority. (TOUR-003)

// Link only the reviewed repository changelog, never an arbitrary URL supplied by an API response.
const CHANGELOG_URL = 'https://github.com/andreivorobiev/virtual-casino-simulator/blob/main/RELEASE_NOTES.md';

// Convert the bounded server contract to text-only copy; missing translations must not leak keys.
export function localizedTour(payload, translate) {
  // Require explicit persistent-account eligibility and the complete bounded merged collection.
  if (payload?.show !== true || payload.persisted !== true || !Array.isArray(payload.entries)
      || payload.entries.length < 1 || payload.entries.length > 3
      || payload.merged_count !== payload.entries.length) return null;
  // Resolve every entry atomically so acknowledging a partial translation cannot hide unseen copy.
  const entries = [];
  // Use only release-coordinator keys from the reviewed shell domain.
  for (const entry of payload.entries) {
    // Refuse arbitrary translation domains, missing keys, and malformed metadata.
    if (!/^whatsNew\.entry\.[0-9_]+\.title$/.test(entry?.title_key)
        || !/^whatsNew\.entry\.[0-9_]+\.body$/.test(entry?.body_key)) return null;
    // Resolve through the application's installed locale/fallback chain.
    const title = translate(entry.title_key);
    // Keep body copy separate from markup and release identifiers.
    const body = translate(entry.body_key);
    // Fail closed on absent, unresolved, or excessively large release copy.
    if (typeof title !== 'string' || !title.trim() || title === entry.title_key || title.length > 200
        || typeof body !== 'string' || !body.trim() || body === entry.body_key || body.length > 2000) return null;
    // Retain localized strings only in the presentation model.
    entries.push({ title, body });
  }
  // Accept only the existing canonical repository-relative changelog location.
  return { entries, changelog: payload.changelog_path === 'RELEASE_NOTES.md' ? CHANGELOG_URL : null };
}

// Own one optional dialog per authenticated shell generation, independent of game rendering.
export function createWhatsNewController({ apiClient, documentRef, windowRef, translate }) {
  // Invalidate late reads and acknowledgements whenever identity or lifecycle changes.
  let generation = 0;
  // Retain only this controller's mounted dialog and localized presentation nodes.
  let mounted = null;

  // Create semantic nodes using textContent so curated copy can never execute as HTML.
  function element(tag, text, testId) {
    // Allocate within the owning document for both production and isolated tests.
    const node = documentRef.createElement(tag);
    // Set plain text only when this node carries copy.
    if (text !== undefined) node.textContent = text;
    // Publish stable test hooks without including release or user identifiers.
    if (testId) node.setAttribute('data-testid', testId);
    // Return the unattached node to its owning composition.
    return node;
  }

  // Remove only this optional surface, optionally returning keyboard focus to its prior owner.
  function removeDialog(restoreFocus) {
    // Capture and clear ownership before native dialog events can run.
    const previous = mounted;
    // Make repeated teardown harmless.
    mounted = null;
    // Stop when no dialog was mounted for this generation.
    if (!previous) return;
    // Close the native top-layer surface before detaching its nodes.
    previous.dialog.close();
    // Remove only this controller's markup.
    previous.dialog.remove();
    // Resolve a fresh shell fallback when a locale rerender replaced the original target.
    const returnFocus = previous.returnFocus?.isConnected && !previous.returnFocus.disabled ? previous.returnFocus : documentRef.querySelector('[data-testid="nav-lobby"]');
    // Restore a live focus target only for a user-initiated close, never after logout.
    if (restoreFocus && returnFocus?.isConnected && !returnFocus.disabled) returnFocus.focus();
  }

  // Discard old session work without storing any local acknowledgement or identity.
  function dispose() {
    // Advance before removing markup so in-flight continuations become inert.
    generation += 1;
    // Teardown must not return focus to a discarded authenticated shell.
    removeDialog(false);
  }

  // Repaint copy in place so a locale transition cannot reset keyboard focus or duplicate the dialog.
  function localize() {
    // Ignore locale events when no optional tour is visible.
    if (!mounted) return;
    // Resolve the entire catalog again through installed fallback dictionaries.
    const tour = localizedTour(mounted.payload, translate);
    // Hide unavailable copy without acknowledging it on the server.
    if (!tour) { removeDialog(true); return; }
    // Keep the dialog heading and introduction synchronized with the shell locale.
    mounted.title.textContent = translate('whatsNew.title');
    // Explain that one merged collection represents meaningful changes since the last acknowledgement.
    mounted.intro.textContent = translate('whatsNew.intro');
    // Update each entry's existing semantic heading and paragraph without replacing focused controls.
    tour.entries.forEach((entry, index) => {
      // Localize the title independently from the body.
      mounted.rows[index].title.textContent = entry.title;
      // Keep translated content inert even if it contains markup characters.
      mounted.rows[index].body.textContent = entry.body;
    });
    // Localize durable acknowledgement independently from session-local deferral.
    mounted.save.textContent = translate(mounted.busy ? 'whatsNew.saving' : 'whatsNew.dismiss');
    // Escape and this secondary control never claim a saved dismissal.
    mounted.later.textContent = translate('whatsNew.later');
    // Keep the full changelog link accessible in the active language.
    mounted.link.textContent = translate('whatsNew.changelog');
    // Show a fixed localized failure, never a raw transport error.
    mounted.error.textContent = mounted.failed ? translate('whatsNew.saveError') : '';
  }

  // Confirm acknowledgement through the existing self-only, empty-body API before closing.
  async function acknowledge(ticket) {
    // Prevent double clicks or a stale control from issuing duplicate work.
    if (!mounted || mounted.busy || ticket !== generation) return;
    // Mark this dialog busy while leaving Not now available during a network failure.
    mounted.busy = true;
    // Clear a previous explicit-attempt failure without retrying automatically.
    mounted.failed = false;
    // Preserve a live in-dialog focus owner before disabling the active submit control.
    if (documentRef.activeElement === mounted.save) mounted.later.focus();
    // Disable only durable acknowledgement while its response is outstanding.
    mounted.save.disabled = true;
    // Announce current progress with localized copy.
    localize();
    // Keep optional tour failures out of login and gameplay control flow.
    try {
      // Send no caller-authored subject, version, session, or consent field.
      const result = await apiClient('/api/v2/me/whats-new/dismiss', { method: 'POST', body: {} });
      // Ignore a response after logout, replacement, or local deferral.
      if (ticket !== generation || !mounted) return;
      // Require explicit durable acknowledgement from the server before claiming success.
      if (result?.dismissed !== true || result.persisted !== true) throw new Error('Unconfirmed acknowledgement');
      // Close only after the durable response and restore the previous keyboard target.
      removeDialog(true);
    } catch (_) {
      // Never repaint a newer account's dialog from an old failed request.
      if (ticket !== generation || !mounted) return;
      // Offer an explicit later attempt and an honest session-local escape hatch.
      mounted.failed = true;
    } finally {
      // Release controls only for the still-owned dialog.
      if (ticket === generation && mounted) {
        // Restore acknowledgement after the single request completes.
        mounted.busy = false;
        // Permit a deliberate user retry without an automatic replay loop.
        mounted.save.disabled = false;
        // Repaint failure or idle text in the current locale.
        localize();
      }
    }
  }

  // Read optional eligibility after authenticated navigation, never delaying shell readiness.
  async function start(session) {
    // Retire any predecessor before checking a replacement identity.
    dispose();
    // Do not read or display the feature for anonymous, terms-gated, or disposable guest sessions.
    if (!session?.user || session.terms?.required || session.user.role === 'guest' || session.user.guest_analytics_id) return false;
    // Bind every asynchronous continuation to this exact shell entry.
    const ticket = generation;
    // Treat unavailable optional endpoints as no tour, preserving compatible deployments.
    try {
      // Eligibility and canonical release selection remain wholly server-owned.
      const payload = await apiClient('/api/v2/me/whats-new');
      // Never display a late response or interrupt another open consent/settings dialog.
      if (ticket !== generation || documentRef.querySelector('dialog[open]')) return false;
      // Reject missing translations and malformed eligibility before creating any visible nodes.
      const tour = localizedTour(payload, translate);
      // Disabled curated catalogs produce no dialog and no acknowledgement request.
      if (!tour) return false;
      // Build one native dialog for focus containment and Escape semantics.
      const dialog = element('dialog', undefined, 'whats-new-dialog');
      // Use a narrowly owned class that cannot restyle game or consent dialogs.
      dialog.className = 'whats-new-dialog';
      // Associate the native dialog with its localized heading and introduction.
      dialog.setAttribute('aria-labelledby', 'whats-new-title');
      // Keep long entries outside the initial screen-reader description.
      dialog.setAttribute('aria-describedby', 'whats-new-intro');
      // Prepare the title as a stable heading rather than a raw release label.
      const title = element('h2');
      // Assign the exact accessible-name target.
      title.id = 'whats-new-title';
      // Prepare the short explanation of merged updates.
      const intro = element('p');
      // Assign the exact accessible-description target.
      intro.id = 'whats-new-intro';
      // Group up to three release entries in one semantic list, not stacked dialogs.
      const list = element('ul', undefined, 'whats-new-entries');
      // Make the single deliberate scroll surface reachable and named for keyboard readers.
      list.tabIndex = 0;
      // Reuse the localized heading without replacing list semantics or inventing release labels.
      list.setAttribute('aria-labelledby', 'whats-new-title');
      // Retain entry nodes for in-place locale updates.
      const rows = tour.entries.map(() => {
        // Use one list item for each release-coordinator entry.
        const item = element('li');
        // Give each meaningful update its own heading.
        const heading = element('h3');
        // Keep longer description text in a wrapping paragraph.
        const body = element('p');
        // Attach only semantic, text-only content.
        item.append(heading, body);
        // Preserve newest-first order supplied by the server.
        list.append(item);
        // Return references for localization without replacing DOM identity.
        return { title: heading, body };
      });
      // Keep the complete changelog accessible without navigating away from a mounted game.
      const link = element('a', undefined, 'whats-new-changelog');
      // Omit unrecognized catalog locations instead of navigating to untrusted origins.
      link.hidden = !tour.changelog;
      // Set only the fixed reviewed repository URL.
      if (tour.changelog) link.href = tour.changelog;
      // Open documentation separately without granting opener access or sending a referrer.
      link.target = '_blank';
      // Preserve both isolation properties explicitly.
      link.rel = 'noopener noreferrer';
      // Reserve an accessible fixed-copy status region for an unconfirmed save.
      const error = element('p', '', 'whats-new-error');
      // Announce a failed acknowledgement without exposing transport details.
      error.setAttribute('role', 'alert');
      // Group controls in a responsive wrapping footer.
      const actions = element('div');
      // Scope the action layout to this dialog.
      actions.className = 'whats-new-actions';
      // Provide honest local deferral independently from saved dismissal.
      const later = element('button', undefined, 'whats-new-later');
      // Avoid implicit form submission in future shell compositions.
      later.type = 'button';
      // Acknowledge only through the existing self-service endpoint.
      const save = element('button', undefined, 'whats-new-dismiss');
      // Keep the primary action outside form and consent semantics.
      save.type = 'button';
      // Preserve canonical primary-action treatment.
      save.className = 'primary';
      // Keep controls stable throughout optional request progress.
      actions.append(later, save);
      // Publish semantic content in reading order.
      dialog.append(title, intro, list, link, error, actions);
      // Restore the prior interactive target, or the Lobby navigation fallback after cold load.
      const returnFocus = documentRef.activeElement === documentRef.body ? documentRef.querySelector('[data-testid="nav-lobby"]') : documentRef.activeElement;
      // Own all state before any dialog event or locale change can fire.
      mounted = { dialog, title, intro, rows, link, error, later, save, payload, returnFocus, busy: false, failed: false };
      // Local deferral removes the dialog without claiming server persistence.
      later.onclick = () => { generation += 1; removeDialog(true); };
      // Escape has the same honest local-only deferral semantics.
      dialog.addEventListener('cancel', event => { event.preventDefault(); later.onclick(); });
      // Keep native top-layer keyboard traversal from handing focus to browser chrome at its boundaries.
      dialog.addEventListener('keydown', event => {
        // Leave ordinary keys and browser-provided movement between interior controls unchanged.
        if (event.key !== 'Tab') return;
        // Omit unavailable controls while preserving the dialog's semantic reading order.
        const controls = [list, link.hidden ? null : link, later, save.disabled ? null : save].filter(Boolean);
        // Select the boundary opposite the user's requested traversal direction.
        const target = event.shiftKey ? controls[controls.length - 1] : controls[0];
        // Wrap only at the matching first/last enabled control.
        if (documentRef.activeElement === (event.shiftKey ? controls[0] : controls[controls.length - 1])) {
          // Prevent browser-chrome traversal while this modal owns interaction.
          event.preventDefault();
          // Restore focus inside the same dialog without replacing nodes or changing route state.
          target.focus();
        }
      });
      // Bind one explicit durable action to this generation.
      save.onclick = () => acknowledge(ticket);
      // Localize all nodes before the native top layer becomes visible.
      localize();
      // Attach outside route outlets so game and locale rerenders cannot recreate the tour.
      documentRef.body.append(dialog);
      // Delegate keyboard focus containment to the native modal implementation.
      dialog.showModal();
      // Start keyboard users at the explicit saved-dismissal action.
      save.focus();
      // Report a visible eligible tour to deterministic tests.
      return true;
    } catch (_) {
      // Remove a partially mounted optional surface only if this request still owns it.
      if (ticket === generation) removeDialog(false);
      // Optional eligibility never prevents login, consent, routing, or gameplay.
      return false;
    }
  }

  // Update text only after the installed locale's dictionaries are ready.
  windowRef.addEventListener('casino-locale-changed', localize);
  // Prevent a frozen page from retaining an old account's optional modal.
  windowRef.addEventListener('pagehide', dispose);
  // Expose only lifecycle operations; no browser-side version or persistence authority exists.
  return { start, dispose };
}
