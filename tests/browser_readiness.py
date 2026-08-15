# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""State-driven readiness helpers for governed Browser acceptance."""

# Import monotonic time so bounded readiness never depends on wall-clock changes.
import time

# Import regular expressions so response predicates accept only governed report identities.
import re


# Read and validate one successful standard-envelope response.
def _response_data(payload: dict, boundary: str) -> dict:
    # Reject missing or malformed response objects before Browser state is trusted.
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        # Include the named boundary without echoing an unbounded server payload.
        raise AssertionError(f"Bingo {boundary} response was not a successful standard envelope")
    # Read the documented response data object.
    data = payload.get("data")
    # Fail closed when the standard envelope omits structured data.
    if not isinstance(data, dict):
        # Name the exact missing response layer for hosted diagnostics.
        raise AssertionError(f"Bingo {boundary} response data was missing or malformed")
    # Return the validated bounded response data.
    return data


# Validate one authoritative won session and return its render descriptor.
def _terminal_descriptor(session: dict, expected_session_id: str | None, boundary: str) -> dict:
    # Require a structured terminal session rather than inferring completion from markup.
    if not isinstance(session, dict) or session.get("status") != "won":
        # Identify the authoritative boundary that did not publish a winner.
        raise AssertionError(f"Bingo {boundary} did not contain a terminal won session")
    # Read the immutable session identity used to bind auto and reload responses.
    session_id = session.get("session_id")
    # Reject absent or changed identity before waiting for any visible card.
    if not isinstance(session_id, str) or not session_id or (expected_session_id is not None and session_id != expected_session_id):
        # Report only the expected and observed bounded identifiers.
        raise AssertionError(f"Bingo {boundary} session identity mismatch: expected={expected_session_id!r} observed={session_id!r}")
    # Read the authoritative winning card retained by the settled session.
    winner_card = session.get("winner_card")
    # Reject a terminal label without the winning-card projection consumed by the UI.
    if not isinstance(winner_card, dict):
        # Keep the diagnostic specific to the missing public projection.
        raise AssertionError(f"Bingo {boundary} terminal session omitted winner_card")
    # Read the exact coordinates that must become visible highlights.
    coordinates = winner_card.get("winning_coords")
    # Require at least one bounded row-column pair before rendering can pass.
    if not isinstance(coordinates, list) or not coordinates or any(not isinstance(coord, list) or len(coord) != 2 or any(not isinstance(value, int) or value < 0 or value > 4 for value in coord) for coord in coordinates):
        # Distinguish malformed terminal state from a delayed route render.
        raise AssertionError(f"Bingo {boundary} winning coordinates were missing or malformed")
    # Return only bounded values required by the route-readiness predicate.
    return {"session_id": session_id, "winning_cell_count": len(coordinates)}


# Prove the compatibility auto response committed one authoritative terminal session.
def require_bingo_terminal_auto_payload(payload: dict) -> dict:
    # Validate the standard envelope returned by the auto endpoint.
    data = _response_data(payload, "auto")
    # Read the authoritative state projection returned with the completed session.
    state = data.get("state")
    # Reject missing state before comparing active and archived ownership.
    if not isinstance(state, dict):
        # Explain the exact fail-closed payload defect.
        raise AssertionError("Bingo auto response state was missing or malformed")
    # Require the terminal action to clear the active slot before remount.
    if state.get("active_session") is not None:
        # Prevent an apparently won response from racing a still-actionable session.
        raise AssertionError("Bingo auto response retained an active session after terminal settlement")
    # Validate the explicit session returned by the mutation.
    descriptor = _terminal_descriptor(data.get("session"), None, "auto response")
    # Read the newest archived session that a fresh route load will select.
    sessions = state.get("last_sessions")
    # Require a non-empty bounded history before accepting the mutation result.
    if not isinstance(sessions, list) or not sessions:
        # Surface an authoritative-state error instead of timing out on markup.
        raise AssertionError("Bingo auto response omitted the terminal session from history")
    # Require history and explicit response to identify the same settled result.
    _terminal_descriptor(sessions[-1], descriptor["session_id"], "auto history")
    # Return the exact descriptor used by the subsequent reload and render gates.
    return descriptor


# Prove a fresh Bingo route load recovered the same authoritative terminal session.
def require_bingo_terminal_reload_payload(payload: dict, expected_session_id: str) -> dict:
    # Validate the standard envelope returned by the route's state request.
    data = _response_data(payload, "reload")
    # Read the provider-authoritative state loaded by the new route mount.
    state = data.get("state")
    # Reject a missing state document before inspecting terminal history.
    if not isinstance(state, dict):
        # Name the malformed reload layer for stable diagnostics.
        raise AssertionError("Bingo reload response state was missing or malformed")
    # Require the settled action to remain non-actionable on the fresh mount.
    if state.get("active_session") is not None:
        # Prevent a stale active session from satisfying visible card selectors.
        raise AssertionError("Bingo reload response resurrected an active session")
    # Read the newest completed session selected by the production mount path.
    sessions = state.get("last_sessions")
    # Fail before DOM polling when no authoritative terminal session exists.
    if not isinstance(sessions, list) or not sessions:
        # Preserve a useful state-bound diagnostic instead of a locator timeout.
        raise AssertionError("Bingo reload response omitted terminal history")
    # Validate exact identity, terminal status, and winning coordinates.
    return _terminal_descriptor(sessions[-1], expected_session_id, "reload history")


# Wait for the mounted Bingo DOM to reflect one already-validated terminal response.
def wait_for_bingo_terminal_render(page, descriptor: dict, *, timeout_seconds: float = 5.0, poll_interval_ms: int = 50, clock=time.monotonic) -> dict:
    # Require the bounded descriptor produced by the authoritative response validators.
    if not isinstance(descriptor, dict) or not isinstance(descriptor.get("session_id"), str) or not isinstance(descriptor.get("winning_cell_count"), int) or descriptor["winning_cell_count"] <= 0:
        # Reject programmer or payload errors before starting a readiness loop.
        raise AssertionError("Bingo terminal render descriptor was missing or malformed")
    # Compute one monotonic deadline without extending the historical five-second budget.
    deadline = clock() + timeout_seconds
    # Retain the newest bounded DOM snapshot for timeout diagnostics.
    last_snapshot = None
    # Poll semantic route state until the authoritative terminal projection is visible.
    while True:
        # Read only stable test ids, highlight count, and the published busy boundary.
        last_snapshot = page.evaluate("""() => { const visible = selector => { const element = document.querySelector(selector); return Boolean(element && element.getClientRects().length); }; return { premium: visible('[data-testid="premium-bingo"]'), card: visible('[data-testid="bingo-card"]'), drawer: visible('[data-testid="bingo-cards-drawer"]'), autoplay: visible('[data-testid="autoplay-bingo"]'), winningCellCount: document.querySelectorAll('[data-winning-cell="true"]').length, busy: document.querySelector('[data-testid="bingo-control-rail"]')?.getAttribute('aria-busy') ?? null }; }""")
        # Accept only the complete terminal surface for the validated winning geometry.
        if isinstance(last_snapshot, dict) and all(last_snapshot.get(key) is True for key in ("premium", "card", "drawer", "autoplay")) and last_snapshot.get("winningCellCount") == descriptor["winning_cell_count"] and last_snapshot.get("busy") == "false":
            # Return the accepted snapshot for final case assertions and evidence.
            return last_snapshot
        # Read the remaining monotonic budget after the current semantic observation.
        remaining = deadline - clock()
        # Fail closed with bounded authoritative and observed dimensions at the deadline.
        if remaining <= 0:
            # Avoid an opaque locator error that hides malformed or stale render state.
            raise AssertionError(f"Bingo terminal render did not become ready for session {descriptor['session_id']!r}: expected_winning_cells={descriptor['winning_cell_count']} observed={last_snapshot!r}")
        # Yield only until the next semantic observation, bounded by the remaining budget.
        page.wait_for_timeout(max(1, min(poll_interval_ms, int(remaining * 1000))))


# Match only the public report identity accepted by the additive Admin route.
ADMIN_FEEDBACK_REPORT_ID = re.compile(r"^report_[A-Za-z0-9_-]+$")


# Validate the authoritative report returned by one Admin triage save.
def require_admin_feedback_save_payload(payload: dict, expected_report_id: str, expected_priority: str, expected_status: str) -> dict:
    # Reject malformed route identities before trusting the response projection.
    if not isinstance(expected_report_id, str) or ADMIN_FEEDBACK_REPORT_ID.fullmatch(expected_report_id) is None:
        # Keep route identity failures distinct from response content failures.
        raise AssertionError("Admin feedback save expected report identity was missing or malformed")
    # Validate the standard successful response envelope.
    data = _response_data(payload, "Admin feedback save")
    # Read the canonical updated report returned by the PATCH route.
    report = data.get("report")
    # Reject missing or malformed updated report data.
    if not isinstance(report, dict):
        # Name the exact missing authoritative layer.
        raise AssertionError("Admin feedback save response omitted structured report data")
    # Require the response to remain bound to the exact opened report.
    if report.get("report_id") != expected_report_id:
        # Preserve bounded expected and observed identities for diagnostics.
        raise AssertionError(f"Admin feedback save report identity mismatch: expected={expected_report_id!r} observed={report.get('report_id')!r}")
    # Require the committed triage fields to equal the action requested by the Browser case.
    if report.get("priority") != expected_priority or report.get("status") != expected_status:
        # Prevent a stale or partially committed save response from unlocking draft preparation.
        raise AssertionError(f"Admin feedback save triage mismatch: expected={expected_priority!r}/{expected_status!r} observed={report.get('priority')!r}/{report.get('status')!r}")
    # Return only the exact committed fields used by the rerender boundary.
    return {"report_id": expected_report_id, "priority": expected_priority, "status": expected_status}


# Save Admin triage and wait until the response-driven detail rerender owns the route.
def save_admin_feedback_triage(page, report_id: str, expected_priority: str, expected_status: str, *, timeout_seconds: float = 5.0, poll_interval_ms: int = 50, clock=time.monotonic) -> dict:
    # Validate bounded arguments before marking or mutating the current test DOM.
    if not isinstance(report_id, str) or ADMIN_FEEDBACK_REPORT_ID.fullmatch(report_id) is None or not isinstance(expected_priority, str) or not isinstance(expected_status, str):
        # Reject invalid helper input before dispatching the PATCH.
        raise AssertionError("Admin feedback save boundary was missing required identity or triage fields")
    # Mark the currently mounted detail so its already-visible selector cannot satisfy readiness.
    marker = f"browser-save-{report_id}"
    # Attach the private test-only marker to the exact old route generation.
    page.get_by_test_id("admin-feedback-detail").evaluate("(element, value) => { element.dataset.browserSaveMarker = value; }", marker)
    # Build the exact report-detail endpoint used by the production save control.
    endpoint = f"/api/v2/admin/feedback/reports/{report_id}"
    # Start one total monotonic response-plus-rerender budget.
    started = clock()
    # Observe the precise PATCH response triggered by the production control.
    try:
        # Enter the response boundary before clicking so fast responses cannot race the test.
        with page.expect_response(lambda response: response.request.method == "PATCH" and response.url.partition("?")[0].endswith(endpoint), timeout=max(1, int(timeout_seconds * 1000))) as response_info:
            # Exercise the real Admin save control.
            page.locator("#feedback-save").click()
    # Convert transport or timeout failures into one stable boundary diagnostic.
    except Exception as error:
        # Preserve only the bounded report identity in the public error.
        raise AssertionError(f"Admin feedback save response did not arrive for report {report_id!r}") from error
    # Validate the canonical response before waiting for the redraw.
    descriptor = require_admin_feedback_save_payload(response_info.value.json(), report_id, expected_priority, expected_status)
    # Compute the remainder of the original total readiness budget.
    deadline = started + timeout_seconds
    # Retain the newest bounded DOM snapshot for timeout diagnostics.
    last_snapshot = None
    # Wait until a new route generation renders the exact committed triage state.
    while True:
        # Inspect route ownership and the two committed triage controls without trusting stale visibility.
        last_snapshot = page.evaluate("""expected => { const detail=document.querySelector('[data-testid="admin-feedback-detail"]'); return { visible:Boolean(detail && detail.getClientRects().length), replaced:Boolean(detail && detail.dataset.browserSaveMarker !== expected.marker), priority:document.querySelector('#feedback-detail-priority')?.value ?? null, status:document.querySelector('#feedback-detail-status')?.value ?? null }; }""", {"marker": marker, "priority": expected_priority, "status": expected_status})
        # Accept only a visible replacement generation with exact committed values.
        if isinstance(last_snapshot, dict) and last_snapshot.get("visible") is True and last_snapshot.get("replaced") is True and last_snapshot.get("priority") == descriptor["priority"] and last_snapshot.get("status") == descriptor["status"]:
            # Return the accepted state for optional downstream evidence.
            return last_snapshot
        # Compute the remaining bounded wait after this semantic observation.
        remaining = deadline - clock()
        # Fail closed when response-driven redraw never takes route ownership.
        if remaining <= 0:
            # Include only the bounded report identity and observed control state.
            raise AssertionError(f"Admin feedback save rerender did not become ready for report {report_id!r}: observed={last_snapshot!r}")
        # Yield briefly before inspecting the next route generation.
        page.wait_for_timeout(max(1, min(poll_interval_ms, int(remaining * 1000))))


# Validate one authoritative manual-only GitHub draft response.
def require_admin_feedback_draft_payload(payload: dict, expected_report_id: str) -> dict:
    # Reject caller-supplied route identities that cannot belong to the governed endpoint.
    if not isinstance(expected_report_id, str) or ADMIN_FEEDBACK_REPORT_ID.fullmatch(expected_report_id) is None:
        # Prevent an ambiguous response predicate or diagnostic from accepting arbitrary text.
        raise AssertionError("Admin feedback draft expected report identity was missing or malformed")
    # Validate the standard response envelope before Browser markup is trusted.
    data = _response_data(payload, "Admin feedback draft")
    # Read the bounded server-sanitized draft projection.
    draft = data.get("draft")
    # Reject a successful envelope without the documented draft object.
    if not isinstance(draft, dict):
        # Identify the missing authoritative layer directly.
        raise AssertionError("Admin feedback draft response omitted structured draft data")
    # Require the response to remain bound to the exact report opened by the Admin.
    if draft.get("source_report_id") != expected_report_id:
        # Report only the bounded expected and observed identifiers.
        raise AssertionError(f"Admin feedback draft report identity mismatch: expected={expected_report_id!r} observed={draft.get('source_report_id')!r}")
    # Require the server-owned manual-only publication safety contract.
    if draft.get("publication_mode") != "manual_only" or draft.get("publication_enabled") is not False:
        # Prevent a changed publication policy from passing through a visible draft selector.
        raise AssertionError("Admin feedback draft response did not preserve manual-only publication")
    # Read the complete reviewable title and body rendered by the Admin surface.
    title, body = draft.get("title"), draft.get("body")
    # Reject missing or blank review content before DOM polling begins.
    if not isinstance(title, str) or not title.strip() or not isinstance(body, str) or not body.strip():
        # Distinguish malformed authoritative content from a delayed browser render.
        raise AssertionError("Admin feedback draft response title or body was missing")
    # Read the governed repository labels included in the manual draft.
    labels = draft.get("labels")
    # Require a bounded string list so malformed response data cannot satisfy the privacy assertion accidentally.
    if not isinstance(labels, list) or not labels or any(not isinstance(label, str) or not label.strip() for label in labels):
        # Name the exact malformed response field.
        raise AssertionError("Admin feedback draft response labels were missing or malformed")
    # Return only the immutable values required by the render gate.
    return {"source_report_id": expected_report_id, "title": title, "body": body, "labels": list(labels)}


# Wait until the Admin draft outlet reflects one already-validated server response.
def wait_for_admin_feedback_draft_render(page, descriptor: dict, *, timeout_seconds: float, poll_interval_ms: int = 50, clock=time.monotonic) -> dict:
    # Reject malformed helper input rather than producing an opaque browser timeout.
    if not isinstance(descriptor, dict) or not isinstance(descriptor.get("title"), str) or not isinstance(descriptor.get("body"), str):
        # Keep programmer errors distinct from delayed rendering.
        raise AssertionError("Admin feedback draft render descriptor was missing or malformed")
    # Preserve the single caller-supplied total deadline across semantic observations.
    deadline = clock() + max(0.0, timeout_seconds)
    # Retain the newest bounded DOM state for a useful fail-closed diagnostic.
    last_snapshot = None
    # Poll the complete manual-draft projection instead of one visibility selector.
    while True:
        # Read only the governed outlet, review fields, copy action, and forbidden external-publication control.
        last_snapshot = page.evaluate("""() => { const outlet=document.querySelector('#feedback-github-draft'); const title=document.querySelector('#feedback-draft-title'); const body=document.querySelector('#feedback-draft-body'); const copy=document.querySelector('#feedback-copy-draft'); return { visible:Boolean(outlet && !outlet.hidden && outlet.getClientRects().length), title:title?.value ?? null, body:body?.value ?? null, copyVisible:Boolean(copy && copy.getClientRects().length), externalCount:document.querySelectorAll('#feedback-open-github').length }; }""")
        # Accept only a visible, complete, exact-response render with no external publication control.
        if isinstance(last_snapshot, dict) and last_snapshot.get("visible") is True and last_snapshot.get("title") == descriptor["title"] and last_snapshot.get("body") == descriptor["body"] and last_snapshot.get("copyVisible") is True and last_snapshot.get("externalCount") == 0:
            # Return the complete accepted snapshot for optional downstream evidence.
            return last_snapshot
        # Compute the remaining portion of the original total budget.
        remaining = deadline - clock()
        # Fail closed when the response-backed surface never becomes complete.
        if remaining <= 0:
            # Include only bounded identity and DOM dimensions in the diagnostic.
            raise AssertionError(f"Admin feedback draft render did not become ready for report {descriptor.get('source_report_id')!r}: observed={last_snapshot!r}")
        # Yield briefly before the next semantic observation without extending the deadline.
        page.wait_for_timeout(max(1, min(poll_interval_ms, int(remaining * 1000))))


# Click the manual draft control and bind its render to the exact authoritative response.
def prepare_admin_feedback_draft(page, report_id: str, *, timeout_seconds: float = 5.0, clock=time.monotonic) -> dict:
    # Validate the route identity before interpolating it into the response predicate.
    if not isinstance(report_id, str) or ADMIN_FEEDBACK_REPORT_ID.fullmatch(report_id) is None:
        # Reject malformed identities before any browser action starts.
        raise AssertionError("Admin feedback draft report identity was missing or malformed")
    # Build the exact documented route suffix for this opened report.
    endpoint = f"/api/v2/admin/feedback/reports/{report_id}/github-draft"
    # Start one total monotonic budget covering response and complete render readiness.
    started = clock()
    # Observe the precise POST consumed by the production click handler.
    try:
        # Enter the response boundary before dispatching the click so fast responses cannot race the test.
        with page.expect_response(lambda response: response.request.method == "POST" and response.url.partition("?")[0].endswith(endpoint), timeout=max(1, int(timeout_seconds * 1000))) as response_info:
            # Exercise the same manual-only control used by an Admin.
            page.locator("#feedback-draft").click()
    # Convert transport or timeout failures into one stable state-bound diagnostic.
    except Exception as error:
        # Avoid leaking unbounded browser internals while retaining the failed report identity.
        raise AssertionError(f"Admin feedback draft response did not arrive for report {report_id!r}") from error
    # Validate the exact response envelope and manual-only policy.
    descriptor = require_admin_feedback_draft_payload(response_info.value.json(), report_id)
    # Preserve only the unused portion of the original five-second budget for rendering.
    remaining = timeout_seconds - (clock() - started)
    # Fail immediately when response completion exhausted the total readiness budget.
    if remaining <= 0:
        # Keep the timeout diagnostic anchored to the authoritative response boundary.
        raise AssertionError(f"Admin feedback draft response exhausted the readiness budget for report {report_id!r}")
    # Wait for the complete exact-response DOM projection within the remaining budget.
    return wait_for_admin_feedback_draft_render(page, descriptor, timeout_seconds=remaining, clock=clock)
