# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""State-driven readiness helpers for governed Browser acceptance."""

# Import monotonic time so bounded readiness never depends on wall-clock changes.
import time


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
