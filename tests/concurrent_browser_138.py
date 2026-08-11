#!/usr/bin/env python3
# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Run the issue #225 exact-138 real-browser qualification on a disposable loopback runtime."""

import argparse  # Parse the immutable qualification profile and artifact locations.
import asyncio  # Coordinate independent browser contexts and the synchronized start barrier.
import json  # Persist only sanitized aggregate qualification evidence.
import math  # Round hosted latency evidence to one stable formal-only deadline quantum.
import os  # Require the explicit disposable-runtime marker before opening local resources.
import shutil  # Remove only the harness-owned copied runtime after listener closure.
import socket  # Prove the exact loopback listener closes after the qualification.
import tempfile  # Select an external disposable runtime parent by default.
import threading  # Serve the test-owned application while the asynchronous browsers run.
import time  # Measure login, gameplay, barrier, and total qualification durations.
from collections import Counter  # Aggregate game assignment, failure, and browser diagnostic counts.
from pathlib import Path  # Resolve source, runtime, and report paths without private-path output.

from casino.config import GAMES  # Discover the current registered game catalog from module metadata.
from tests import ui_50000  # Reuse exact-source UI drivers and secret-safe browser helpers.

# Require exactly the issue-owned number of independent synthetic browser users.
USER_COUNT = 138
# Preserve the issue-owned minimum concurrent-user floor without silently weakening it.
MINIMUM_USERS_PER_GAME = 3
# Bound setup at the synchronized login gate before the harness releases any context.
BARRIER_TIMEOUT_SECONDS = 180
# Bound simultaneous context creation and shell navigation so the loopback runtime is observed under controlled admission.
SETUP_ADMISSION_LIMIT = 12
# Bound the formal post-barrier login to one absolute window above the observed 64.265-second hosted maximum.
FORMAL_LOGIN_DEADLINE_MS = 90_000
# Preserve the terminal third-run successful gameplay p95 as the public data point for deadline policy.
OBSERVED_GAMEPLAY_SUCCESS_P95_MS = 85_071
# Preserve the terminal third-run successful gameplay maximum as the public tail data point.
OBSERVED_GAMEPLAY_SUCCESS_MAX_MS = 88_788
# Add one fixed thirty-second safety margin to the hosted successful p95.
FORMAL_GAMEPLAY_P95_MARGIN_MS = 30_000
# Require at least fifteen seconds beyond the hosted successful maximum.
FORMAL_GAMEPLAY_MAX_MARGIN_MS = 15_000
# Round the derived deadline upward to a stable five-second evidence quantum.
FORMAL_GAMEPLAY_DEADLINE_QUANTUM_MS = 5_000
# Refuse a formal gameplay window longer than two and one-half minutes.
FORMAL_GAMEPLAY_DEADLINE_HARD_CAP_MS = 150_000
# Publish only fixed low-cardinality phases for aggregate completion and failure evidence.
FORMAL_PHASES = ("context_setup", "barrier", "login_gate", "locale_selection", "credential_entry", "terms_acceptance", "login_response", "authenticated_lobby", "gameplay_navigation", "navigation_return_lobby", "navigation_lobby_ready", "navigation_route_open", "navigation_game_ready", "gameplay_action", "context_cleanup")  # Keep every aggregate phase fixed and low-cardinality.
# Keep otherwise unclassified failures inside one fixed aggregate bucket.
FORMAL_FAILURE_PHASES = (*FORMAL_PHASES, "unclassified")
# Publish only fixed low-cardinality action states inside the assigned game-action phase.
FORMAL_ACTION_STATES = ("driver_selection", "initial_ready", "wager_selection", "action_commit", "decision_resolution", "settlement_ready", "next_action_ready", "generic_driver")  # Keep action-state attribution independent of selectors, players, and payloads.
# Keep otherwise unclassified game-action failures inside one fixed aggregate state bucket.
FORMAL_FAILURE_ACTION_STATES = (*FORMAL_ACTION_STATES, "unclassified")
# Bind the formal report to permanent requirement and browser-test identities.
REQUIREMENT_IDS = ("AUTH-001", "AUTH-002", "SESSION-001", "SESSION-005", "TEST-039", "TEST-042", "TEST-142", "CORE-021")
# Reuse canonical game order so catalog growth changes the plan deterministically.
GAME_IDS = tuple(game["id"] for game in GAMES)
# Map each single-request catalog gap to its visible preparation controls and terminal action.
SIMPLE_ONE_ACTION_DRIVERS = {
    "boule": ((("[data-number]", 1),), '[data-testid="boule-spin"]'),  # Select one rendered number and spin the boule.
    "coin_pusher": ((), '[data-testid="coin-pusher-drop"]'),  # Drop one rendered coin with the default visible stake.
    "color_wheel": ((("[data-color]", 1),), '[data-testid="color-wheel-spin"]'),  # Select one rendered colour and spin.
    "daily_draw_lab": ((("[data-number]", 1),), '[data-testid="daily-draw-lab-go"]'),  # Mark one rendered number and draw.
    "faro": ((("[data-rank]", 1),), '[data-testid="faro-deal"]'),  # Select one rendered rank and deal.
    "lucky_grid": ((("[data-cell]", 3),), '[data-testid="lucky-grid-go"]'),  # Select the exact three rendered cells and reveal.
    "marble_race": ((("[data-bet]", 1), ("[data-marble]", 1)), '[data-testid="marble-race-go"]'),  # Select a market and marble before racing.
    "pachinko": ((), '[data-testid="pachinko-drop"]'),  # Drop one rendered ball with the default visible stake.
    "pattern_draw": ((("[data-bet]", 1),), '[data-testid="pattern-draw-draw"]'),  # Select one rendered pattern and draw.
    "poker_dice": ((), '[data-testid="poker-dice-roll"]'),  # Roll the five rendered poker dice once.
    "trente_et_quarante": ((("[data-bet]", 1),), '[data-testid="teq-deal"]'),  # Select one rendered coup wager and deal.
}
# Name the four decision games whose complete visible cycle requires more than one request.
DECISION_ONE_ACTION_GAMES = frozenset({"four_card_poker", "mississippi_stud", "pai_gow_poker", "teen_patti"})
# Pin the exact fifteen catalog gaps accepted from the governed failure artifact.
CATALOG_GAP_GAME_IDS = tuple((*SIMPLE_ONE_ACTION_DRIVERS, *sorted(DECISION_ONE_ACTION_GAMES)))
# Name the exact eleven inherited long-suite drivers that exceeded the bounded formal gameplay window.
FORMAL_BOUNDED_GAME_IDS = frozenset(
    {
        "baccarat",  # Replace refund/rebet coverage with one ready wager and settled coup.
        "big_six_wheel",  # Replace broad input rotation with one visible wager and spin.
        "bingo",  # Replace autoplay/reset coverage with one purchased-card action.
        "blackjack",  # Replace rare-control balancing with one deterministic settled hand.
        "double_bonus_video_poker",  # Replace mode/hold coverage with one deal/draw cycle.
        "jacks_or_better_video_poker",  # Replace mode/hold coverage with one deal/draw cycle.
        "keno",  # Replace board/refund coverage with one quick-pick ticket and draw.
        "multi_hand_video_poker",  # Replace mode/hold coverage with one deal/draw cycle.
        "roulette",  # Replace table-wide pointer coverage with one wager and spin.
        "scratch_cards",  # Replace cell-coverage rotation with one card settlement.
        "slots",  # Keep one ready spin without shared autoplay coverage.
    }
)
# Bind each bounded draw-poker driver to its game-owned rendered deal and draw selector contract.
FORMAL_DRAW_POKER_SELECTORS = {
    "double_bonus_video_poker": ("[data-deal]", "[data-draw]"),  # Match Double Bonus's dedicated data attributes.
    "jacks_or_better_video_poker": ('[data-action="deal"]', '[data-action="draw"]'),  # Match the shared action attributes.
    "multi_hand_video_poker": ('[data-action="deal"]', '[data-action="draw"]'),  # Match the shared action attributes.
}
# Derive the exact three affected draw-poker module identities from the governed selector contracts.
FORMAL_DRAW_POKER_GAME_IDS = frozenset(FORMAL_DRAW_POKER_SELECTORS)


# Derive one formal-only gameplay deadline from successful hosted latency evidence and fixed policy bounds.
def derive_formal_gameplay_deadline_ms(
    p95_ms=OBSERVED_GAMEPLAY_SUCCESS_P95_MS,  # Accept the preserved successful hosted p95.
    maximum_ms=OBSERVED_GAMEPLAY_SUCCESS_MAX_MS,  # Accept the preserved successful hosted maximum.
    p95_margin_ms=FORMAL_GAMEPLAY_P95_MARGIN_MS,  # Accept the fixed p95 safety margin.
    maximum_margin_ms=FORMAL_GAMEPLAY_MAX_MARGIN_MS,  # Accept the fixed tail safety margin.
    quantum_ms=FORMAL_GAMEPLAY_DEADLINE_QUANTUM_MS,  # Accept the stable rounding quantum.
    hard_cap_ms=FORMAL_GAMEPLAY_DEADLINE_HARD_CAP_MS,  # Accept the formal-only absolute hard cap.
):  # Keep every policy input explicit for listener-free regression coverage.
    # Normalize every policy input to an integer millisecond value.
    values = tuple(int(value) for value in (p95_ms, maximum_ms, p95_margin_ms, maximum_margin_ms, quantum_ms, hard_cap_ms))
    # Reject absent or negative observed latency and nonpositive rounding/cap policy.
    if values[0] < 0 or values[1] < 0 or values[2] < 0 or values[3] < 0 or values[4] < 1 or values[5] < 1:
        # Keep a malformed policy from silently weakening the fail-closed formal profile.
        raise ValueError("formal gameplay deadline policy requires nonnegative latency and positive quantum/cap")
    # Preserve the larger of the p95-plus-margin and maximum-plus-tail-margin bounds.
    evidence_bound_ms = max(values[0] + values[2], values[1] + values[3])
    # Round upward so minor hosted timing variance cannot change the published deadline by milliseconds.
    rounded_bound_ms = int(math.ceil(evidence_bound_ms / values[4]) * values[4])
    # Apply the documented hard cap without changing ordinary browser timeouts.
    return min(rounded_bound_ms, values[5])


# Bind the formal profile to the documented hosted evidence formula at import time.
FORMAL_GAMEPLAY_DEADLINE_MS = derive_formal_gameplay_deadline_ms()


# Build one deterministic all-catalog assignment without opening a listener or browser.
def build_assignment_plan(game_ids=GAME_IDS, user_count=USER_COUNT, minimum_users_per_game=MINIMUM_USERS_PER_GAME):
    # Normalize the caller-owned immutable identities before arithmetic checks.
    normalized_games = tuple(str(game_id).strip() for game_id in game_ids)
    # Reject an empty, duplicate, or malformed catalog before allocating synthetic users.
    if not normalized_games or any(not game_id for game_id in normalized_games) or len(set(normalized_games)) != len(normalized_games):
        # Keep the diagnostic independent of any private runtime state.
        raise ValueError("registered game catalog must contain unique nonempty identifiers")
    # Require the exact issue-owned user count for every formal plan.
    if int(user_count) != USER_COUNT:
        # Refuse a shortened or expanded run that could be mistaken for issue acceptance.
        raise ValueError(f"formal qualification requires exactly {USER_COUNT} users")
    # Normalize the declared coverage floor as one positive integer.
    required_floor = int(minimum_users_per_game)
    # Reject disabled coverage before checking the catalog capacity.
    if required_floor < 1:
        # Preserve at least one real UI player for every registered game.
        raise ValueError("minimum users per game must be positive")
    # Calculate the smallest user population able to satisfy the declared current-catalog floor.
    minimum_required_users = len(normalized_games) * required_floor
    # Fail before any local resource opens when the exact population cannot cover the complete catalog.
    if minimum_required_users > USER_COUNT:
        # Publish only safe aggregate counts needed to reconcile the stale issue criterion.
        raise ValueError(
            f"catalog coverage requires {minimum_required_users} users "
            f"({len(normalized_games)} games x {required_floor}) but the formal profile requires exactly {USER_COUNT}"
        )
    # Divide the complete user population evenly across canonical catalog order.
    base, remainder = divmod(USER_COUNT, len(normalized_games))
    # Build one stable public assignment row per synthetic ordinal.
    assignments = []
    # Allocate every registered game a contiguous deterministic user range.
    for game_index, game_id in enumerate(normalized_games):
        # Give the canonical prefix one extra user until the exact remainder is exhausted.
        quota = base + (1 if game_index < remainder else 0)
        # Reject any plan that would violate the issue-owned per-game floor.
        if quota < required_floor:
            # Defend the same arithmetic invariant even if allocation logic changes later.
            raise ValueError("deterministic game allocation is below the required concurrent-user floor")
        # Append each synthetic ordinal without retaining credentials or account identifiers.
        for _ in range(quota):
            # Derive the next zero-based stable user ordinal.
            user_index = len(assignments)
            # Record only the public catalog assignment.
            assignments.append({"user_index": user_index, "game_id": game_id, "game_index": game_index})
    # Require exact, gap-free user accounting before returning the plan.
    if [row["user_index"] for row in assignments] != list(range(USER_COUNT)):
        # Refuse duplicate, missing, or reordered synthetic identities.
        raise AssertionError("user allocation is not exact and contiguous")
    # Return the complete deterministic all-catalog plan.
    return assignments


# Coordinate one exact set of browser contexts at the pre-login release boundary.
class StartBarrier:
    # Initialize immutable party count and asynchronous state.
    def __init__(self, parties):
        # Require a positive exact participant count.
        if int(parties) < 1:
            # Reject a disabled barrier before any task starts.
            raise ValueError("barrier parties must be positive")
        # Store the expected number of independently created contexts.
        self.parties = int(parties)
        # Count contexts that reached the rendered login gate.
        self.ready = 0
        # Track the greatest observed ready count for terminal evidence.
        self.peak_ready = 0
        # Serialize arrival accounting across asynchronous tasks.
        self._lock = asyncio.Lock()
        # Signal the controller only when every expected context is waiting.
        self.all_ready = asyncio.Event()
        # Release all waiting contexts from one controller-owned boundary.
        self.release = asyncio.Event()

    # Mark one independent context ready and wait for the controller release.
    async def wait(self):
        # Serialize exact arrival accounting.
        async with self._lock:
            # Count this context exactly once.
            self.ready += 1
            # Reject accidental double-arrival or an oversized worker plan.
            if self.ready > self.parties:
                # Fail the offending task without corrupting the public count.
                raise AssertionError("more contexts reached the barrier than expected")
            # Preserve the highest synchronized ready count.
            self.peak_ready = max(self.peak_ready, self.ready)
            # Signal the controller when the exact expected population is waiting.
            if self.ready == self.parties:
                # Allow the controller to capture the full barrier before releasing work.
                self.all_ready.set()
        # Wait until the controller has observed the complete population or a fail-closed timeout.
        await self.release.wait()


# Return one bounded no-path diagnostic for terminal aggregate evidence.
def safe_error(error):
    # Reuse the existing qualification scrubber so browser framework messages cannot expose private paths.
    return ui_50000.safe_error(error)


# Summarize successful latency values without retaining user-level timing rows.
def latency_summary(values):
    # Delegate nearest-rank p50/p95/p99 and maximum calculations to the established UI harness.
    return ui_50000.latency_summary(values)


# Load and validate the exact-source Package B 1/2/4/8 preflight artifact.
def load_pool_preflight(path, source_commit):
    # Resolve the caller-provided evidence path without including it in terminal output.
    evidence_path = Path(path).expanduser().resolve()
    # Refuse evidence stored inside the source checkout.
    if evidence_path == ui_50000.ROOT.resolve() or ui_50000.ROOT.resolve() in evidence_path.parents:
        # Keep generated measurement data outside source control.
        raise ValueError("pool preflight must be outside the source checkout")
    # Parse the secret-safe exact-source aggregate packet.
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    # Require only the documented top-level evidence fields.
    if set(evidence) != {"source_commit", "measurements", "pool"}:
        # Reject stale or expanded evidence schemas.
        raise ValueError("pool preflight schema is invalid")
    # Require the same immutable checkout as the browser qualification.
    if evidence["source_commit"] != source_commit:
        # Refuse foreign-head performance evidence.
        raise ValueError("pool preflight source does not match qualification source")
    # Read the exact four governed measurement rows.
    measurements = evidence["measurements"]
    # Require one row for each Package B concurrency level in order.
    if [row.get("concurrency") for row in measurements] != [1, 2, 4, 8]:
        # Reject missing, duplicate, or reordered load levels.
        raise ValueError("pool preflight must contain concurrency 1, 2, 4, and 8")
    # Allow only aggregate numeric measurement fields.
    measurement_fields = {"concurrency", "p50_ms", "p95_ms", "throughput_rps", "errors"}
    # Reject identity-bearing or free-form fields from every row.
    if any(set(row) != measurement_fields for row in measurements):
        # Keep browser artifacts free of connector and request detail.
        raise ValueError("pool preflight measurement schema is invalid")
    # Require zero errors and positive throughput for each bounded packet.
    if any(int(row["errors"]) != 0 or float(row["throughput_rps"]) <= 0 for row in measurements):
        # Refuse a failed storage preflight before any browser resource starts.
        raise ValueError("pool preflight contains an error or empty throughput")
    # Read the fixed-cardinality Package B pool snapshot.
    pool = evidence["pool"]
    # Require the exact documented snapshot field set.
    allowed_pool_fields = {
        "capacity",  # Preserve the configured connection ceiling.
        "in_use",  # Preserve the current leased-connection count.
        "idle",  # Preserve the reusable idle-connection count.
        "waiting",  # Preserve the current lease-waiter count.
        "physical_created",  # Preserve the physical connection creation count.
        "reused",  # Preserve the successful connection-reuse count.
        "discarded",  # Preserve the rejected connection count.
        "wait_count",  # Preserve the cumulative lease-wait count.
        "timeout_count",  # Preserve the cumulative lease-timeout count.
        "rollback_cleanup",  # Preserve the rollback cleanup count.
        "connector_error",  # Preserve the connector failure count.
        "wait_buckets_ms",  # Preserve the fixed low-cardinality latency buckets.
    }
    # Reject missing or additional pool fields.
    if set(pool) != allowed_pool_fields:
        # Preserve one fixed low-cardinality artifact contract.
        raise ValueError("pool preflight snapshot schema is invalid")
    # Require no error, exhaustion, lease, or waiter residue.
    if (
        int(pool["timeout_count"]) != 0
        or int(pool["connector_error"]) != 0
        or int(pool["in_use"]) != 0
        or int(pool["waiting"]) != 0
    ):
        # Stop before a browser run when the bounded pool gate is red.
        raise ValueError("pool preflight did not finish cleanly")
    # Require physical creation to remain within configured capacity.
    if not 0 < int(pool["physical_created"]) <= int(pool["capacity"]):
        # Reject absent or unbounded physical-connection evidence.
        raise ValueError("pool preflight physical connection count is invalid")
    # Return the validated secret-safe packet.
    return evidence


# Build a sanitized aggregate pool snapshot or an explicit non-MySQL observation.
def pool_snapshot():
    # Import storage only after the explicit disposable profile has been validated.
    from casino.core import storage

    # Resolve the process-local provider that served every browser request.
    provider = storage.get_storage_provider()
    # Read the optional fixed-cardinality pool snapshot seam.
    snapshot = getattr(provider, "pool_snapshot", None)
    # Return an explicit provider-only observation when JSON storage owns the disposable run.
    if not callable(snapshot):
        # Preserve the absence of MySQL pool counters without fabricating zeros.
        return {"provider": "json", "available": False}
    # Capture only the Package B fixed-cardinality mapping.
    values = snapshot()
    # Allow only documented low-cardinality gauges, counters, policy, and wait buckets.
    allowed = {
        "capacity",
        "in_use",
        "idle",
        "waiting",
        "physical_created",
        "reused",
        "discarded",
        "wait_count",
        "timeout_count",
        "rollback_cleanup",
        "connector_error",
        "wait_buckets_ms",
    }
    # Reject any unexpected field before writing the report.
    if set(values).difference(allowed):
        # Prevent future free-form or identity-bearing metrics from entering evidence automatically.
        raise AssertionError("MySQL pool snapshot contains an unapproved field")
    # Publish the bounded snapshot under the explicit provider identity.
    return {"provider": "mysql", "available": True, **values}


# Start one test-owned in-process loopback server so Package B metrics remain inspectable.
def start_loopback_server():
    # Import the runtime adapter only after the disposable data root is fixed by process environment.
    from casino import app
    # Import startup helpers used by the normal local server.
    from casino.core import auth, players
    # Import the provider bootstrap and selected data directories.
    from casino.core.state_store import ensure_dirs, migrate_from_v7_if_needed
    # Import the provider-neutral player bootstrap.
    from casino.core.storage import bootstrap_players

    # Prepare only the explicit disposable runtime directories.
    ensure_dirs()
    # Apply only the existing local-format data migration inside the disposable root.
    migrate_from_v7_if_needed()
    # Bootstrap default players through the selected disposable provider.
    bootstrap_players(players.default_players)
    # Bootstrap the synthetic default Admin used only for setup and aggregate evidence.
    auth.bootstrap_admin_from_env()
    # Ask the operating system for one test-owned loopback listener after runtime setup succeeds.
    server = app.CasinoThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    # Resolve the exact assigned local port without publishing it in artifacts.
    port = int(server.server_address[1])
    # Run the request server on one named test-owned daemon thread.
    thread = threading.Thread(target=server.serve_forever, name="casino-225-loopback", daemon=True)
    # Start accepting loopback requests.
    thread.start()
    # Build the established bounded API client without retaining endpoint details in reports.
    client = ui_50000.ApiClient(f"http://127.0.0.1:{port}")
    # Poll the real login endpoint for at most twenty seconds.
    for _ in range(200):
        # Treat startup connection failures as transient only inside the bounded loop.
        try:
            # Establish the setup-only Admin session.
            client.login_default_user()
            # Return tracked resources after the service is genuinely ready.
            return server, thread, client
        # Retry only until the bounded readiness deadline.
        except Exception:
            # Give the thread a short opportunity to accept requests.
            time.sleep(0.1)
    # Stop the exact test-owned listener after a failed readiness probe.
    stop_loopback_server(server, thread)
    # Fail without printing private runtime or network details.
    raise RuntimeError("disposable qualification server did not become ready")


# Stop one exact in-process server and verify its listener is closed.
def stop_loopback_server(server, thread):
    # Capture the assigned test-only port before closing the server socket.
    port = int(server.server_address[1])
    # Request cooperative termination of the serve-forever loop.
    server.shutdown()
    # Close the exact listener socket after the request loop exits.
    server.server_close()
    # Join only the harness-owned thread.
    thread.join(timeout=10)
    # Reject a stranded server thread.
    if thread.is_alive():
        # Keep cleanup failure explicit and secret-safe.
        raise AssertionError("qualification server thread did not stop")
    # Probe only the exact previously assigned loopback port.
    with socket.socket() as probe:
        # Bound the final closure check.
        probe.settimeout(0.2)
        # Treat connection refusal as the required terminal state.
        closed = probe.connect_ex(("127.0.0.1", port)) != 0
    # Reject a listener that survived server closure.
    if not closed:
        # Do not expose the ephemeral port in the error.
        raise AssertionError("qualification loopback listener remained open")
    # Return only the public cleanup boolean.
    return {"closed": True}


# Provision one synthetic account through the allowed setup-only Admin API.
def create_synthetic_user(client, user_index, locale):
    # Build a reserved-domain identifier that can never receive real mail.
    email = f"browser-138-{user_index:03d}@example.invalid"
    # Build an in-memory test-only password unique to this disposable runtime.
    password = f"Browser138-{user_index:03d}-Synthetic!"
    # Submit the account through the documented Admin boundary.
    created = client.call(
        "/api/v1/admin/users",
        "POST",
        {
            "email": email,
            "password": password,
            "display_name": f"Browser 138 {user_index:03d}",
            "initial_tokens": 1_000_000,
            "terms_accepted": True,
            "language": locale,
            "format_locale": locale,
        },
    )
    # Keep credentials and canonical identities in memory only.
    return {
        "email": email,
        "password": password,
        "user_id": created["user"]["user_id"],
        "player_id": created["user"]["player_id"],
    }


# Run one asynchronous shell setup beneath the explicit admission bound and record aggregate concurrency.
async def run_admitted_setup(admission, counters, counter_lock, operation):
    # Wait for one setup slot without delaying contexts that already reached the login barrier.
    async with admission:
        # Serialize low-cardinality active and peak setup accounting.
        async with counter_lock:
            # Count this setup only after its semaphore slot is owned.
            counters["active_setup"] += 1
            # Preserve the greatest simultaneous pre-barrier setup population.
            counters["peak_setup"] = max(counters["peak_setup"], counters["active_setup"])
        # Always release active setup accounting even when navigation fails.
        try:
            # Execute the caller-owned context creation and visible-login preparation.
            return await operation()
        # Close the aggregate admission observation around every terminal path.
        finally:
            # Serialize the exact decrement before releasing the semaphore context.
            async with counter_lock:
                # Remove this setup from the active population.
                counters["active_setup"] -= 1


# Submit the already-rendered login form beneath the formal absolute deadline.
async def login_from_rendered_gate(page, base_url, user, locale, activated_counts, phase_observer):
    # Reuse the pre-barrier page and refuse the redundant synchronized navigation from the failed hosted run.
    await ui_50000.login_through_ui(page, base_url, user, locale, activated_counts, navigate=False, deadline_ms=FORMAL_LOGIN_DEADLINE_MS, phase_observer=phase_observer)


# Select one or more distinct enabled rendered controls through the established pointer helper.
async def select_visible_controls(page, selector, count, ordinal, activated_counts):
    # Discover only currently enabled controls for the declared public selector.
    controls = await ui_50000.enabled_locators(page, selector)
    # Require enough distinct controls to satisfy the game-owned visible preparation.
    if len(controls) < int(count):
        # Keep the diagnostic bounded to the public catalog game surface.
        raise AssertionError("visible one-action preparation controls unavailable")
    # Activate the requested number of distinct controls in deterministic rotating order.
    for offset in range(int(count)):
        # Click the rendered control through the same real-pointer helper as the established harness.
        await ui_50000.click_locator(controls[(int(ordinal) + offset) % len(controls)], activated_counts)


# Complete one visible action for each catalog game absent from the established 50,000-cycle driver.
async def play_catalog_gap_ui(page, game_id, ordinal, seen_counts, activated_counts):
    # Resolve the eleven single-request games through their fixed visible selector contract.
    simple_driver = SIMPLE_ONE_ACTION_DRIVERS.get(game_id)
    # Run a simple rendered selection-and-terminal-action cycle when one is declared.
    if simple_driver is not None:
        # Split visible preparation controls from the terminal action selector.
        preparations, terminal_selector = simple_driver
        # Apply every game-owned preparation before the action becomes eligible.
        for selector, count in preparations:
            # Select the exact bounded number of rendered controls.
            await select_visible_controls(page, selector, count, ordinal, activated_counts)
        # Commit and settle one visible game action.
        await ui_50000.terminal_action(page, terminal_selector, activated_counts)
    # Complete one Four Card Poker deal and rendered play decision.
    elif game_id == "four_card_poker":
        # Deal the visible five-card player hand.
        await ui_50000.click_control(page, "[data-deal]", activated_counts)
        # Require the rendered multiplier choices before selecting one.
        await ui_50000.wait_any_enabled(page, ["[data-play]"])
        # Select one legal visible play multiplier.
        await select_visible_controls(page, "[data-play]", 1, ordinal, activated_counts)
        # Require terminal deal-again readiness after settlement.
        await ui_50000.wait_any_enabled(page, ["[data-deal]"])
    # Complete all three Mississippi Stud decision streets with visible minimum bets.
    elif game_id == "mississippi_stud":
        # Deal the visible hole cards and first community street.
        await ui_50000.click_control(page, "[data-deal]", activated_counts)
        # Advance the exact three governed streets without leaving an open wager.
        for street in range(3):
            # Require a rendered legal bet at this street.
            await ui_50000.wait_any_enabled(page, ["[data-bet]"])
            # Rotate among the visible legal multipliers while preserving a complete cycle.
            await select_visible_controls(page, "[data-bet]", 1, ordinal + street, activated_counts)
        # Require terminal deal-again readiness after the river settlement.
        await ui_50000.wait_any_enabled(page, ["[data-deal]"])
    # Complete one Pai Gow Poker deal through the rendered house-way decision.
    elif game_id == "pai_gow_poker":
        # Require deterministic initial-deal readiness before the first rendered pointer action.
        await ui_50000.wait_any_enabled(page, ['[data-action="deal"]'])
        # Deal the visible seven-card setting hand.
        await ui_50000.click_control(page, '[data-action="deal"]', activated_counts)
        # Require the game-owned automatic legal arrangement control.
        await ui_50000.wait_any_enabled(page, ['[data-action="house-way"]'])
        # Settle the hand through the rendered house-way action.
        await ui_50000.click_control(page, '[data-action="house-way"]', activated_counts)
        # Require terminal next-deal readiness after settlement.
        await ui_50000.wait_any_enabled(page, ['[data-action="deal"]'])
    # Complete one Teen Patti deal and rendered play decision.
    elif game_id == "teen_patti":
        # Deal the visible three-card player hand.
        await ui_50000.click_control(page, "[data-deal]", activated_counts)
        # Require the rendered play decision before settlement.
        await ui_50000.wait_any_enabled(page, ["[data-play]"])
        # Commit the visible play action.
        await ui_50000.click_control(page, "[data-play]", activated_counts)
        # Require terminal next-deal readiness in the wager panel.
        await ui_50000.wait_any_enabled(page, ["[data-deal]"])
    # Let the established full driver own every catalog game outside the accepted gap set.
    else:
        # Report that no concurrent-only driver was selected.
        return False
    # Record the terminal rendered state without persisting per-user controls.
    await ui_50000.inventory_controls(page, seen_counts)
    # Report successful ownership of this catalog gap.
    return True


# Run one awaitable browser operation while publishing a fixed action-state boundary.
async def run_formal_action_state(action_state_observer, state, operation):
    # Mark the fixed low-cardinality state active before its browser operation begins.
    action_state_observer(state, "started")
    # Await the caller-owned browser operation without creating a new timeout budget.
    result = await operation
    # Mark the fixed state complete only after its browser operation succeeds.
    action_state_observer(state, "completed")
    # Return any selector or action result needed by the next bounded state.
    return result


# Complete one bounded ready/action/settlement cycle for each diagnosed inherited long-suite driver.
async def play_formal_bounded_ui(page, game_id, ordinal, seen_counts, activated_counts, action_state_observer):
    # Keep ordinary UI50K coverage unchanged by selecting only the eleven diagnosed formal games.
    if game_id not in FORMAL_BOUNDED_GAME_IDS:
        # Report that another explicit or inherited driver owns this game.
        return False
    # Inventory the assigned route once without exercising configuration or shared autoplay coverage.
    await ui_50000.inventory_controls(page, seen_counts)
    # Complete one Roulette wager and spin without the long-suite table-wide pointer schedule.
    if game_id == "roulette":
        # Require one visible straight-up wager target before pointer activation.
        await run_formal_action_state(action_state_observer, "initial_ready", ui_50000.wait_any_enabled(page, ['[data-testid^="roulette-num-"]']))
        # Resolve the currently actionable number targets after readiness.
        numbers = await ui_50000.enabled_locators(page, '[data-testid^="roulette-num-"]')
        # Refuse a disappeared table rather than converting it to a generic deadline.
        if not numbers:
            # Preserve one public readiness diagnostic for this game.
            raise AssertionError("Roulette number targets unavailable")
        # Add one deterministic straight-up wager and await its committed drawer row.
        await run_formal_action_state(action_state_observer, "wager_selection", ui_50000.roulette_add_bet(page, numbers[int(ordinal) % len(numbers)], activated_counts))
        # Commit the real visible spin without running unrelated table coverage.
        await run_formal_action_state(action_state_observer, "action_commit", ui_50000.click_control(page, '[data-testid="roulette-spin"]', activated_counts))
        # Require the committed disabled resolving state before accepting a later ready button.
        roulette_resolving = """() => { const result = document.querySelector('[data-testid=\"roulette-result-region\"]'); const spin = document.querySelector('[data-testid=\"roulette-spin\"]'); return Boolean(result?.dataset.phase === 'spinning' && spin?.disabled); }"""
        # Attribute a missing resolving transition separately from next-round readiness.
        await run_formal_action_state(
            action_state_observer,  # Attribute this wait to the task-local fixed state observer.
            "settlement_ready",  # Separate resolving transition from pointer commit and next readiness.
            page.wait_for_function(roulette_resolving, timeout=ui_50000.operation_timeout_ms(ui_50000.ACTION_TIMEOUT_MS)),  # Reuse the remaining formal deadline.
        )
        # Require a genuinely enabled fresh-spin control after settlement.
        await run_formal_action_state(action_state_observer, "next_action_ready", ui_50000.wait_any_enabled(page, ['[data-testid="roulette-spin"]']))
    # Complete one Slots spin without creating a shared autoplay session.
    elif game_id == "slots":
        # Require the rendered spin action before committing it.
        await run_formal_action_state(action_state_observer, "initial_ready", ui_50000.wait_any_enabled(page, ['[data-testid="slots-spin"]']))
        # Commit one visible spin.
        await run_formal_action_state(action_state_observer, "action_commit", ui_50000.click_control(page, '[data-testid="slots-spin"]', activated_counts))
        # Allow the request-owned busy rerender to replace the pre-click enabled spin control.
        await page.wait_for_timeout(5)
        # Require next-spin readiness after the reel result settles.
        await run_formal_action_state(action_state_observer, "next_action_ready", ui_50000.wait_any_enabled(page, ['[data-testid="slots-spin"]']))
    # Complete one five-number Keno ticket without broad board or refund coverage.
    elif game_id == "keno":
        # Normalize a retained result only when its public new-ticket action is ready.
        new_ticket = page.get_by_test_id("keno-new-ticket")
        # Start a fresh ticket through the visible UI when the prior disposable state retained a result.
        if await ui_50000.locator_ready(new_ticket):
            # Reset only this assigned player's disposable ticket state.
            await run_formal_action_state(action_state_observer, "initial_ready", ui_50000.click_locator(new_ticket, activated_counts))
        # Require the bounded five-number helper before selection.
        await run_formal_action_state(action_state_observer, "initial_ready", ui_50000.wait_any_enabled(page, ["#quick5"]))
        # Select exactly five visible numbers.
        await run_formal_action_state(action_state_observer, "wager_selection", ui_50000.click_control(page, "#quick5", activated_counts))
        # Purchase the selected player-scoped ticket.
        await run_formal_action_state(action_state_observer, "action_commit", ui_50000.click_control(page, '[data-testid="keno-buy"]', activated_counts))
        # Require the public draw action after purchase.
        await run_formal_action_state(action_state_observer, "settlement_ready", ui_50000.wait_any_enabled(page, ['[data-testid="keno-draw"]']))
        # Draw and settle the purchased ticket.
        await run_formal_action_state(action_state_observer, "decision_resolution", ui_50000.click_control(page, '[data-testid="keno-draw"]', activated_counts))
        # Require terminal new-ticket readiness after the draw animation.
        await run_formal_action_state(action_state_observer, "next_action_ready", ui_50000.wait_any_enabled(page, ['[data-testid="keno-new-ticket"]']))
    # Complete one Bingo card purchase and require the next legal call action.
    elif game_id == "bingo":
        # Require a fresh card-purchase state without starting shared autoplay.
        await run_formal_action_state(action_state_observer, "initial_ready", ui_50000.wait_any_enabled(page, ['[data-testid="bingo-buy"]']))
        # Purchase one visible synthetic card.
        await run_formal_action_state(action_state_observer, "action_commit", ui_50000.click_control(page, '[data-testid="bingo-buy"]', activated_counts))
        # Require the rendered next legal action after the wager commits.
        await run_formal_action_state(action_state_observer, "next_action_ready", ui_50000.wait_any_enabled(page, ['[data-testid="bingo-call"]']))
    # Complete one Blackjack hand with deterministic legal decisions rather than deficit balancing.
    elif game_id == "blackjack":
        # Require one fresh-hand action before the first wager.
        await run_formal_action_state(action_state_observer, "initial_ready", ui_50000.wait_any_enabled(page, ['[data-testid="blackjack-deal"]']))
        # Deal one public hand.
        await run_formal_action_state(action_state_observer, "action_commit", ui_50000.click_control(page, '[data-testid="blackjack-deal"]', activated_counts))
        # Allow the request-owned decision rerender to replace the pre-click enabled deal control.
        await page.wait_for_timeout(5)
        # Mark the bounded legal-decision loop as one fixed public action state.
        action_state_observer("decision_resolution", "started")
        # Resolve at most twelve legal states before requiring a terminal next deal.
        for _step in range(12):
            # Prefer terminal readiness, then deterministic settlement actions, then progress actions.
            choice = await ui_50000.wait_any_enabled(
                page,  # Reuse this task's rendered Blackjack table.
                [
                    '[data-testid="blackjack-deal"]',  # Prefer terminal next-hand readiness.
                    '[data-testid="blackjack-stand"]',  # Prefer deterministic ordinary settlement.
                    '[data-testid="blackjack-surrender"]',  # Resolve a legal surrender state.
                    '[data-testid="blackjack-even-money"]',  # Resolve a legal natural decision.
                    '[data-testid="blackjack-insurance"]',  # Resolve a legal insurance decision.
                    '[data-testid="blackjack-double"]',  # Prefer a one-action terminal wager when legal.
                    '[data-testid="blackjack-hit"]',  # Advance an ordinary nonterminal hand.
                    '[data-testid="blackjack-split"]',  # Preserve progress when split is the remaining legal action.
                ],
            )
            # Stop immediately when the table exposes a fresh-hand action.
            if choice == '[data-testid="blackjack-deal"]':
                # Mark the deterministic decision sequence terminal.
                action_state_observer("decision_resolution", "completed")
                # Leave the bounded loop after exact next-hand readiness.
                break
            # Dispatch the first currently legal deterministic decision through the real pointer path.
            await ui_50000.click_control(page, choice, activated_counts)
            # Allow the next decision or settlement rerender to replace the clicked control.
            await page.wait_for_timeout(5)
        # Reject cycling or stranded hands rather than masking them with a longer global deadline.
        else:
            # Preserve one exact game-owned readiness diagnostic.
            raise AssertionError("Blackjack formal driver did not reach next-deal readiness within 12 decisions")
        # Publish the already-observed terminal fresh-hand boundary as a separate fixed state.
        await run_formal_action_state(action_state_observer, "next_action_ready", ui_50000.wait_any_enabled(page, ['[data-testid="blackjack-deal"]']))
    # Complete one Baccarat wager and coup without the long-suite refund/rebet cycle.
    elif game_id == "baccarat":
        # Require the asynchronous wager rail before selection.
        await run_formal_action_state(action_state_observer, "initial_ready", ui_50000.wait_any_enabled(page, ["[data-bet]"]))
        # Select one deterministic visible wager zone.
        await run_formal_action_state(action_state_observer, "wager_selection", select_visible_controls(page, "[data-bet]", 1, ordinal, activated_counts))
        # Require the wager response to expose its removable committed row.
        await run_formal_action_state(action_state_observer, "settlement_ready", ui_50000.wait_any_enabled(page, ["[data-clear]"]))
        # Deal and settle the committed coup.
        await run_formal_action_state(action_state_observer, "action_commit", ui_50000.click_control(page, '[data-testid="baccarat-deal"]', activated_counts))
        # Allow the reveal-phase rerender to replace the pre-click enabled deal control.
        await page.wait_for_timeout(5)
        # Require next-coup readiness after the reveal theater finishes.
        await run_formal_action_state(action_state_observer, "next_action_ready", ui_50000.wait_any_enabled(page, ['[data-testid="baccarat-deal"]']))
    # Complete one bounded deal/draw cycle for the three diagnosed draw-poker modules.
    elif game_id in FORMAL_DRAW_POKER_GAME_IDS:
        # Resolve the game-owned DOM contract instead of assuming all three modules share action attributes.
        deal_selector, draw_selector = FORMAL_DRAW_POKER_SELECTORS[game_id]
        # Require the game-specific initial deal control without rotating long-suite configuration.
        await run_formal_action_state(action_state_observer, "initial_ready", ui_50000.wait_any_enabled(page, [deal_selector]))
        # Deal the player hand through the same game-specific visible control.
        await run_formal_action_state(action_state_observer, "action_commit", ui_50000.click_control(page, deal_selector, activated_counts))
        # Require the game-specific legal draw action without broad hold-position coverage.
        await run_formal_action_state(action_state_observer, "decision_resolution", ui_50000.wait_any_enabled(page, [draw_selector]))
        # Settle the hand through the matching game-specific public draw control.
        await run_formal_action_state(action_state_observer, "settlement_ready", ui_50000.click_control(page, draw_selector, activated_counts))
        # Require terminal next-hand readiness.
        await run_formal_action_state(action_state_observer, "next_action_ready", ui_50000.wait_any_enabled(page, [deal_selector]))
    # Complete one Big Six wager and spin without rotating every wager input.
    elif game_id == "big_six_wheel":
        # Require at least one visible wager input.
        await run_formal_action_state(action_state_observer, "initial_ready", ui_50000.wait_any_enabled(page, ["[data-wager]"]))
        # Fill one deterministic wager while clearing no unrelated outcome fields in the fresh disposable state.
        wagers = await ui_50000.enabled_locators(page, "[data-wager]")
        # Refuse a disappeared wager rail after readiness.
        if not wagers:
            # Preserve one exact game-owned readiness diagnostic.
            raise AssertionError("Big Six wager inputs unavailable")
        # Enter one bounded synthetic-token wager.
        await run_formal_action_state(action_state_observer, "wager_selection", ui_50000.fill_control(wagers[int(ordinal) % len(wagers)], "1", activated_counts))
        # Commit one public spin.
        await run_formal_action_state(action_state_observer, "action_commit", ui_50000.click_control(page, "[data-spin]", activated_counts))
        # Allow the resolving rerender to replace the pre-click enabled spin control.
        await page.wait_for_timeout(5)
        # Require fresh-spin readiness after settlement.
        await run_formal_action_state(action_state_observer, "next_action_ready", ui_50000.wait_any_enabled(page, ["[data-spin]"]))
    # Complete one Scratch Card purchase and settlement without rotating coverage across all cells.
    elif game_id == "scratch_cards":
        # Require a fresh-card purchase action.
        await run_formal_action_state(action_state_observer, "initial_ready", ui_50000.wait_any_enabled(page, ['[data-action="start"]']))
        # Purchase one synthetic card.
        await run_formal_action_state(action_state_observer, "action_commit", ui_50000.click_control(page, '[data-action="start"]', activated_counts))
        # Require at least one covered rendered cell after the purchase response.
        await run_formal_action_state(action_state_observer, "settlement_ready", ui_50000.wait_any_enabled(page, ['[data-testid^="scratch-cell-"]']))
        # Resolve one covered cell through the public pointer path before using reveal-all.
        cells = await ui_50000.enabled_locators(page, '[data-testid^="scratch-cell-"]')
        # Refuse a disappeared card after readiness.
        if not cells:
            # Preserve one exact game-owned readiness diagnostic.
            raise AssertionError("Scratch Card exposed no covered cells")
        # Reveal one deterministic covered cell.
        await run_formal_action_state(action_state_observer, "decision_resolution", ui_50000.click_locator(cells[int(ordinal) % len(cells)], activated_counts))
        # Settle the remaining covered cells through the public action.
        await run_formal_action_state(action_state_observer, "settlement_ready", ui_50000.click_control(page, '[data-action="reveal-all"]', activated_counts))
        # Require a fresh-card action after all nine cells settle.
        await run_formal_action_state(action_state_observer, "next_action_ready", ui_50000.wait_any_enabled(page, ['[data-action="start"]']))
    # Record the terminal rendered state without persisting user-level controls.
    await ui_50000.inventory_controls(page, seen_counts)
    # Report successful ownership of this diagnosed formal driver.
    return True


# Run navigation and one visible action beneath one formal task-local absolute deadline.
async def run_formal_gameplay(page, assignment, seen_counts, activated_counts, phase_observer, action_state_observer):
    # Convert the fixed millisecond policy to one monotonic absolute deadline shared by every nested browser operation.
    absolute_deadline = time.perf_counter() + (FORMAL_GAMEPLAY_DEADLINE_MS / 1000)
    # Install the deadline only in this asynchronous browser task so ordinary profiles and sibling contexts stay isolated.
    deadline_token = ui_50000.FORMAL_OPERATION_DEADLINE.set(absolute_deadline)

    # Execute the fixed navigation and action phases under the same absolute deadline.
    async def operation():
        # Record aggregate catalog-navigation work independently from the game-owned action.
        phase_observer("gameplay_navigation", "started")
        # Navigate through the catalog UI while emitting fixed public navigation subphases.
        await ui_50000.navigate_to_game(
            page,  # Reuse the authenticated task-owned page.
            assignment["game_id"],  # Select only the assigned public game.
            activated_counts,  # Preserve aggregate rendered-control evidence.
            assignment["user_index"],  # Retain deterministic route-selection coverage.
            phase_observer=phase_observer,  # Emit only fixed navigation subphases.
        )
        # Record terminal catalog navigation after the game route is ready.
        phase_observer("gameplay_navigation", "completed")
        # Record the visible game-action phase.
        phase_observer("gameplay_action", "started")
        # Record fixed driver-selection attribution before choosing a bounded or inherited path.
        action_state_observer("driver_selection", "started")
        # Resolve explicit ownership without beginning any game action under the selection state.
        gap_owned = assignment["game_id"] in CATALOG_GAP_GAME_IDS
        # Resolve whether the diagnosed formal-only readiness driver owns this game.
        bounded_owned = assignment["game_id"] in FORMAL_BOUNDED_GAME_IDS
        # Record driver selection complete before any game-owned action begins.
        action_state_observer("driver_selection", "completed")
        # Start with no completed explicit driver.
        explicit_completed = False
        # Run one of the exact fifteen accepted catalog-gap drivers.
        if gap_owned:
            # Attribute the established bounded gap cycle to one fixed driver state.
            action_state_observer("generic_driver", "started")
            # Complete the declared gap driver through visible controls.
            explicit_completed = await play_catalog_gap_ui(
                page,  # Reuse the task-owned rendered game route.
                assignment["game_id"],  # Select the assigned public catalog driver.
                assignment["user_index"],  # Preserve deterministic visible action choice.
                seen_counts,  # Collect aggregate ready and terminal controls.
                activated_counts,  # Collect aggregate pointer activation evidence.
            )
            # Record the bounded gap driver terminal only after it succeeds.
            action_state_observer("generic_driver", "completed")
        # Run one of the exact eleven diagnosed formal-only readiness drivers.
        elif bounded_owned:
            # Complete the formal-specific ready/action/settlement cycle.
            explicit_completed = await play_formal_bounded_ui(
                page,  # Reuse the task-owned rendered game route.
                assignment["game_id"],  # Select the assigned public game.
                assignment["user_index"],  # Preserve deterministic visible choices.
                seen_counts,  # Collect only aggregate rendered-control evidence.
                activated_counts,  # Collect only aggregate pointer activation evidence.
                action_state_observer,  # Emit fixed low-cardinality action states.
            )
        # Require player-scoped wager evidence for every bounded catalog-gap driver.
        action_evidence = "wager_required"
        # Delegate every already-covered game to the established exact-source UI driver.
        if not explicit_completed:
            # Attribute inherited long-suite execution to one fixed generic state.
            action_state_observer("generic_driver", "started")
            # Complete one existing game-owned action and capture its actual wager/non-wager classification.
            action_evidence = await ui_50000.play_game_ui(
                page,  # Reuse the task-owned rendered game route.
                assignment["game_id"],  # Select the assigned inherited game driver.
                assignment["user_index"],  # Preserve deterministic action selection.
                seen_counts,  # Collect aggregate control observations.
                activated_counts,  # Collect aggregate pointer activations.
            )
            # Record terminal inherited-driver completion.
            action_state_observer("generic_driver", "completed")
        # Refuse missing or expanded action classifications before evidence collection.
        if action_evidence not in {"wager_required", "non_wager"}:
            # Keep the diagnostic fixed and independent of any account or gameplay payload.
            raise AssertionError("formal gameplay action produced an invalid ledger expectation")
        # Record terminal visible game action.
        phase_observer("gameplay_action", "completed")
        # Return one fixed action-aware expectation to post-browser isolation evidence.
        return action_evidence

    # Always release the task-local deadline even when navigation, action, or cancellation fails.
    try:
        # Enforce the absolute bound independently of Playwright so loops cannot create fresh operation budgets.
        return await asyncio.wait_for(operation(), timeout=FORMAL_GAMEPLAY_DEADLINE_MS / 1000)
    # Convert either the outer bound or an exhausted nested remaining-time calculation to one stable signature.
    except (asyncio.TimeoutError, TimeoutError) as error:
        # Preserve one public fail-closed deadline diagnostic.
        raise AssertionError("formal gameplay absolute deadline exceeded") from error
    # Restore the caller's prior context after every terminal path.
    finally:
        # Remove only this task's formal timeout override.
        ui_50000.FORMAL_OPERATION_DEADLINE.reset(deadline_token)


# Run one independent browser context from the rendered login gate through one complete game play.
async def run_user(browser, client, assignment, user, barrier, setup_admission, counters, counter_lock):
    # Derive one deterministic locale without introducing a user-visible allowlist.
    locale = "en-US" if assignment["user_index"] % 2 == 0 else "ru-RU"
    # Start without browser resources so partial setup remains cleanable.
    context = None
    # Start one fail-closed aggregate result without account identifiers.
    result = {"game_id": assignment["game_id"], "barrier_ready": False, "login_ok": False, "gameplay_ok": False, "ledger_expectation": "unclassified", "context_closed": False, "completed_phases": []}  # Keep one sanitized task result with fixed aggregate flags only.
    # Track the active fixed phase for one bounded terminal failure bucket.
    current_phase = None
    # Track the active fixed game-action state for precise bounded readiness attribution.
    current_action_state = None
    # Track completed fixed phases without publishing per-user activity rows.
    completed_phases = set()
    # Track completed fixed action states without publishing per-user selector histories.
    completed_action_states = set()

    # Record one fixed phase transition for this task-local result.
    def observe_phase(name, status):
        # Rebind the task-local active phase after validating the fixed schema.
        nonlocal current_phase
        # Reject accidental selector, account, URL, or other high-cardinality phase labels.
        if name not in FORMAL_PHASES:
            # Keep the diagnostic independent of any private task state.
            raise ValueError("formal phase observer received an unknown phase")
        # Mark the active phase when a governed operation starts.
        if status == "started":
            # Preserve only the fixed phase identity.
            current_phase = name
        # Mark a fixed phase complete after its terminal operation succeeds.
        elif status == "completed":
            # Add the fixed identity to the task-local aggregate set.
            completed_phases.add(name)
            # Clear the active phase only when the matching phase completed.
            if current_phase == name:
                # Avoid attributing later failures to an already-completed phase.
                current_phase = None
        # Refuse ungoverned status values before they reach the artifact.
        else:
            # Preserve one bounded schema diagnostic.
            raise ValueError("formal phase observer received an unknown status")

    # Record one fixed action-state transition for this task-local result.
    def observe_action_state(name, status):
        # Rebind the task-local active action state after validating the fixed schema.
        nonlocal current_action_state
        # Reject selectors, payloads, and other high-cardinality action-state labels.
        if name not in FORMAL_ACTION_STATES:
            # Keep the diagnostic independent of any private task state.
            raise ValueError("formal action-state observer received an unknown state")
        # Mark the fixed action state active before its governed browser operation.
        if status == "started":
            # Preserve only the fixed low-cardinality state identity.
            current_action_state = name
        # Mark the fixed action state terminal only after its operation succeeds.
        elif status == "completed":
            # Add the state to the task-local aggregate set.
            completed_action_states.add(name)
            # Clear the active state only when the matching state completed.
            if current_action_state == name:
                # Avoid attributing later failures to an already-completed state.
                current_action_state = None
        # Refuse ungoverned status values before they reach the artifact.
        else:
            # Preserve one bounded schema diagnostic.
            raise ValueError("formal action-state observer received an unknown status")
    # Collect only grouped credential-free browser diagnostics for this context.
    diagnostics = {"console_errors": Counter(), "page_errors": Counter(), "http_failures": Counter()}
    # Track whether this page has completed real form authentication for state-aware diagnostic filtering.
    authentication_state = {"authenticated": False}
    # Start protected browser work so cookies and session storage always close.
    try:
        # Define one admitted context-and-shell setup that releases its slot before the synchronized barrier wait.
        async def prepare_login_gate():
            # Rebind the outer context handle so terminal cleanup always owns it.
            nonlocal context
            # Create one independent cookie, cache, and session-storage boundary.
            context = await browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
            # Open one page owned only by this synthetic account.
            page = await context.new_page()
            # Attach state-aware grouped diagnostics before the first anonymous request.
            ui_50000.attach_page_diagnostics(
                page,
                diagnostics,
                anonymous_probe_active=lambda: not authentication_state["authenticated"],
            )
            # Navigate to the public shell beneath bounded setup admission.
            await page.goto(client.base_url, wait_until="domcontentloaded", timeout=ui_50000.SETUP_TIMEOUT_MS)
            # Require the rendered login gate before releasing the setup slot.
            await page.get_by_test_id("login-gate").wait_for(state="visible", timeout=ui_50000.SETUP_TIMEOUT_MS)
            # Return the admitted page while its independent context remains alive at the barrier.
            return page

        # Record bounded pre-barrier context setup.
        observe_phase("context_setup", "started")
        # Prepare this shell beneath the controller-owned admission semaphore.
        page = await run_admitted_setup(setup_admission, counters, counter_lock, prepare_login_gate)
        # Record terminal context setup after the rendered gate is visible.
        observe_phase("context_setup", "completed")
        # Mark this exact independent context ready.
        result["barrier_ready"] = True
        # Record synchronized barrier waiting.
        observe_phase("barrier", "started")
        # Wait until all 138 contexts are ready and the controller releases them together.
        await barrier.wait()
        # Record terminal barrier release.
        observe_phase("barrier", "completed")
        # Start aggregate login timing immediately after the synchronized release.
        login_started = time.perf_counter()
        # Track rendered login controls without persisting individual control histories.
        activated_counts = Counter()
        # Authenticate through the already-rendered real localized form without another navigation.
        await login_from_rendered_gate(page, client.base_url, user, locale, activated_counts, observe_phase)
        # Close the anonymous diagnostic window only after the real login flow succeeds.
        authentication_state["authenticated"] = True
        # Preserve only the successful aggregate latency sample.
        result["login_seconds"] = time.perf_counter() - login_started
        # Record successful authentication.
        result["login_ok"] = True
        # Count a concurrently active gameplay task under one async lock.
        async with counter_lock:
            # Increment current active gameplay after successful login.
            counters["active_gameplay"] += 1
            # Preserve the peak simultaneous gameplay population.
            counters["peak_gameplay"] = max(counters["peak_gameplay"], counters["active_gameplay"])
        # Start the rendered navigation-and-play latency sample.
        play_started = time.perf_counter()
        # Track only task-local rendered control observations.
        seen_counts = Counter()
        # Start protected gameplay concurrency accounting.
        try:
            # Run catalog navigation and one visible action beneath the formal absolute gameplay deadline.
            result["ledger_expectation"] = await run_formal_gameplay(
                page,  # Reuse the authenticated task-owned page.
                assignment,  # Preserve the public game and deterministic ordinal.
                seen_counts,  # Collect only task-local control observations.
                activated_counts,  # Collect only task-local pointer activations.
                observe_phase,  # Emit fixed aggregate phase transitions.
                observe_action_state,  # Emit fixed aggregate game-action states.
            )
            # Preserve only the successful aggregate gameplay latency sample.
            result["play_seconds"] = time.perf_counter() - play_started
            # Record one terminal UI play.
            result["gameplay_ok"] = True
        # Always release active-gameplay accounting after completion or failure.
        finally:
            # Serialize the decrement so peak accounting remains exact.
            async with counter_lock:
                # Remove this task from the active gameplay population.
                counters["active_gameplay"] -= 1
    # Convert browser or product failure into one bounded aggregate signature.
    except Exception as error:
        # Retain no user, credential, URL query, path, or raw log detail.
        result["error"] = safe_error(error)
        # Preserve only the active fixed phase or one bounded fallback bucket.
        result["failure_phase"] = current_phase or "unclassified"
        # Preserve only the active fixed action state when failure occurred inside gameplay.
        result["failure_action_state"] = current_action_state or "unclassified"
    # Always destroy this independent browser context.
    finally:
        # Close cookies, cache, pages, and session storage when context creation succeeded.
        if context is not None:
            # Record the fixed cleanup phase before releasing the independent context.
            observe_phase("context_cleanup", "started")
            # Release the exact test-owned browser context.
            await context.close()
            # Record successful context cleanup.
            result["context_closed"] = True
            # Record terminal context cleanup.
            observe_phase("context_cleanup", "completed")
        # Convert the task-local set into fixed canonical order for aggregate counting.
        result["completed_phases"] = [phase for phase in FORMAL_PHASES if phase in completed_phases]
        # Convert the task-local action-state set into fixed canonical order for aggregate counting.
        result["completed_action_states"] = [state for state in FORMAL_ACTION_STATES if state in completed_action_states]
        # Convert diagnostic counters to deterministic JSON mappings.
        result["browser_diagnostics"] = {name: dict(counter.most_common()) for name, counter in diagnostics.items()}
    # Return one sanitized task result without account identifiers.
    return result


# Validate post-run account and action-aware ledger isolation through setup-only Admin APIs.
def collect_isolation_evidence(client, users, results):
    # Require one terminal task result for each synthetic account before pairing private in-memory identities.
    if len(users) != len(results):
        # Refuse misaligned action evidence rather than attributing one player's ledger to another result.
        raise ValueError("isolation evidence requires one result per synthetic user")
    # Track canonical player identities only in memory.
    player_ids = [user["player_id"] for user in users]
    # Count duplicated canonical player identities.
    duplicate_player_ids = len(player_ids) - len(set(player_ids))
    # Track globally duplicated immutable ledger identifiers.
    ledger_ids = []
    # Track per-player action identities so one settlement cannot commit twice.
    duplicate_action_keys = 0
    # Count users whose state remained bound to the provisioned player.
    matching_players = 0
    # Count users whose wallet remained nonnegative.
    nonnegative_balances = 0
    # Count users with at least one gameplay ledger event beyond the setup grant.
    users_with_gameplay_ledger = 0
    # Count successful actions whose rendered path committed a wager and therefore requires exact game-owned ledger evidence.
    wager_evidence_required = 0
    # Count required wager actions with at least one matching player-scoped game ledger row.
    wager_evidence_satisfied = 0
    # Count successful rendered actions that explicitly completed without committing a wager.
    non_wager_actions = 0
    # Count non-wager actions that unexpectedly mutated the assigned game's ledger.
    non_wager_actions_with_ledger = 0
    # Count successful actions with one accepted wager/non-wager expectation.
    classified_gameplay_actions = 0
    # Inspect every synthetic account sequentially after browser activity has stopped.
    for user, result in zip(users, results):
        # Read only this account's bounded Admin state.
        state = client.call(f"/api/v2/admin/users/{user['user_id']}/state")
        # Count the canonical player binding without persisting either identity.
        matching_players += int(state["player_id"] == user["player_id"])
        # Count nonnegative synthetic wallet state.
        nonnegative_balances += int(float(state["token_balance"]) >= 0)
        # Read this player's bounded ledger through the player-filtered-before-limit evidence API.
        rows = client.call(f"/api/v1/players/{user['player_id']}/ledger?limit=100")["ledger"]
        # Keep immutable ledger identifiers in memory only for duplicate detection.
        ledger_ids.extend(str(row.get("ledger_id") or "") for row in rows if row.get("ledger_id"))
        # Exclude the one setup grant before requiring gameplay ledger evidence.
        gameplay_rows = [row for row in rows if row.get("transaction_type") != "ADMIN_TOKEN_GRANT"]
        # Count users with at least one game-owned ledger movement.
        users_with_gameplay_ledger += int(bool(gameplay_rows))
        # Isolate only rows owned by the assigned public game before evaluating this action's expectation.
        assigned_game_rows = [row for row in gameplay_rows if str(row.get("game") or "") == str(result.get("game_id") or "")]
        # Evaluate ledger expectations only for a terminally successful visible gameplay action.
        if result.get("gameplay_ok"):
            # Resolve the fixed expectation produced by the actual rendered action path.
            expectation = result.get("ledger_expectation")
            # Require game-owned ledger evidence when the rendered action committed a wager.
            if expectation == "wager_required":
                # Count one fail-closed wager expectation.
                wager_evidence_required += 1
                # Count satisfaction only from this exact player's assigned-game ledger rows.
                wager_evidence_satisfied += int(bool(assigned_game_rows))
                # Count one accepted action classification.
                classified_gameplay_actions += 1
            # Accept an explicitly classified non-wager action without fabricating a debit or settlement.
            elif expectation == "non_wager":
                # Count one legitimate visible no-wager completion.
                non_wager_actions += 1
                # Keep unexpected game-owned money movement red rather than treating no-wager as optional evidence.
                non_wager_actions_with_ledger += int(bool(assigned_game_rows))
                # Count one accepted action classification.
                classified_gameplay_actions += 1
        # Build bounded action identities only when the ledger exposes an idempotency key.
        action_keys = [
            (str(row.get("game") or ""), str(row["details"]["ledger_action_key"]))
            for row in gameplay_rows
            if isinstance(row.get("details"), dict) and row["details"].get("ledger_action_key")
        ]
        # Count duplicate action identities inside this player's ledger.
        duplicate_action_keys += len(action_keys) - len(set(action_keys))
    # Count globally duplicated ledger row identities.
    duplicate_ledger_ids = len(ledger_ids) - len(set(ledger_ids))
    # Return only aggregate isolation and duplicate-settlement evidence.
    return {
        "unique_player_count": len(set(player_ids)),
        "duplicate_player_id_count": duplicate_player_ids,
        "matching_player_count": matching_players,
        "nonnegative_balance_count": nonnegative_balances,
        "users_with_gameplay_ledger": users_with_gameplay_ledger,
        "wager_evidence_required": wager_evidence_required,  # Publish the count of successful actions that committed wagers.
        "wager_evidence_satisfied": wager_evidence_satisfied,  # Publish exact assigned-game row satisfaction.
        "non_wager_actions": non_wager_actions,  # Publish legitimate visible no-wager completions.
        "non_wager_actions_with_ledger": non_wager_actions_with_ledger,  # Publish unexpected money movement on no-wager paths.
        "classified_gameplay_actions": classified_gameplay_actions,  # Publish recognized action expectations.
        "duplicate_ledger_id_count": duplicate_ledger_ids,
        "duplicate_action_key_count": duplicate_action_keys,
    }


# Build the terminal aggregate report and exact acceptance status.
def aggregate_results(assignments, results, barrier, counters, isolation, pool, pool_preflight, source_commit, elapsed_seconds):
    # Aggregate deterministic assignment counts for every current catalog game.
    assigned_by_game = Counter(row["game_id"] for row in assignments)
    # Aggregate successful terminal gameplay counts by game.
    successful_by_game = Counter(row["game_id"] for row in results if row.get("gameplay_ok"))
    # Group bounded task failure signatures.
    failure_counts = Counter(row.get("error") for row in results if row.get("error"))
    # Count completed fixed phases without retaining user-level rows.
    completed_phase_counts = Counter(phase for row in results for phase in row.get("completed_phases", ()))
    # Count the terminal fixed failure phase for each failed task.
    failed_phase_counts = Counter(row.get("failure_phase", "unclassified") for row in results if row.get("error"))
    # Count completed fixed action states without retaining user-level rows.
    completed_action_state_counts = Counter(state for row in results for state in row.get("completed_action_states", ()))
    # Count the terminal fixed action state for each failed task.
    failed_action_state_counts = Counter(row.get("failure_action_state", "unclassified") for row in results if row.get("error"))
    # Attribute each bounded public failure signature to its assigned game, fixed phase, and fixed action state.
    failure_attribution_counts = Counter(  # Aggregate only sanitized public attribution dimensions.
        (  # Build one stable four-part attribution key.
            str(row.get("game_id") or "controller"),  # Retain only the public assigned game.
            str(row.get("failure_phase") or "unclassified"),  # Retain one fixed phase.
            str(row.get("failure_action_state") or "unclassified"),  # Retain one fixed action state.
            str(row.get("error")),  # Retain one scrubbed bounded error signature.
        )
        for row in results  # Visit each sanitized task result.
        if row.get("error")  # Exclude successful rows from failure attribution.
    )
    # Merge grouped browser diagnostics without retaining user-level rows.
    diagnostics = {"console_errors": Counter(), "page_errors": Counter(), "http_failures": Counter()}
    # Visit every terminal context result.
    for row in results:
        # Read its already-sanitized diagnostic groups.
        for name, values in row.get("browser_diagnostics", {}).items():
            # Add the grouped counts to the aggregate category.
            diagnostics[name].update(values)
    # Select successful login timings only.
    login_latencies = [row["login_seconds"] for row in results if "login_seconds" in row]
    # Select successful terminal gameplay timings only.
    play_latencies = [row["play_seconds"] for row in results if "play_seconds" in row]
    # Build explicit boolean gates so one failure cannot be hidden by totals.
    gates = {
        "exact_users": len(assignments) == USER_COUNT and len(results) == USER_COUNT,  # Require exact assignment and result populations.
        "setup_admission": counters["active_setup"] == 0  # Require every admitted setup to release its aggregate slot.
        and 0 < counters["peak_setup"] <= SETUP_ADMISSION_LIMIT,  # Prove startup reached a positive bounded peak.
        "barrier": barrier.ready == USER_COUNT and barrier.peak_ready == USER_COUNT,  # Require every context at the synchronized gate.
        "authentication": sum(bool(row.get("login_ok")) for row in results) == USER_COUNT,  # Require every rendered login to succeed.
        "gameplay": sum(bool(row.get("gameplay_ok")) for row in results) == USER_COUNT,  # Require every visible game action to settle.
        "action_state_attribution": all(  # Require driver ownership for every authenticated task.
            "driver_selection" in row.get("completed_action_states", ())  # Require every task that entered gameplay to record driver ownership.
            for row in results  # Inspect each aggregate-only result.
            if row.get("login_ok")  # Exclude tasks that never reached game navigation.
        )
        and all(  # Require concrete fixed-state attribution for each game-action failure.
            row.get("failure_action_state") in FORMAL_ACTION_STATES  # Require a fixed concrete state for every game-action failure.
            for row in results  # Inspect each aggregate-only result.
            if row.get("error") and row.get("failure_phase") == "gameplay_action"  # Limit state attribution to the game-action phase.
        ),
        "catalog_coverage": set(assigned_by_game) == set(GAME_IDS)  # Require assignments for the complete registered catalog.
        and min(assigned_by_game.values(), default=0) >= MINIMUM_USERS_PER_GAME  # Preserve the three-user assignment floor.
        and min(successful_by_game.values(), default=0) >= MINIMUM_USERS_PER_GAME,  # Preserve the three-user success floor.
        "browser_diagnostics": not any(diagnostics[name] for name in diagnostics),  # Refuse grouped browser, page, or HTTP failures.
        "isolation": isolation["unique_player_count"] == USER_COUNT  # Require one canonical player per synthetic account.
        and isolation["duplicate_player_id_count"] == 0  # Refuse duplicate account-to-player bindings.
        and isolation["matching_player_count"] == USER_COUNT  # Require every response to bind the expected player.
        and isolation["nonnegative_balance_count"] == USER_COUNT  # Require every post-action wallet to remain solvent.
        and isolation["classified_gameplay_actions"] == USER_COUNT  # Require every successful action to declare one fixed ledger expectation.
        and isolation["wager_evidence_satisfied"] == isolation["wager_evidence_required"]  # Require exact player-scoped assigned-game rows for every wagering action.
        and isolation["non_wager_actions_with_ledger"] == 0  # Refuse unexpected game-owned money movement for legitimate no-wager actions.
        and isolation["duplicate_ledger_id_count"] == 0  # Refuse duplicate ledger identities.
        and isolation["duplicate_action_key_count"] == 0,  # Refuse duplicate settlement action identities.
        "context_cleanup": sum(bool(row.get("context_closed")) for row in results) == USER_COUNT,  # Require every browser context to close.
        "pool": not pool.get("available")  # Permit JSON-only fallback evidence without inventing MySQL counters.
        or (  # Otherwise require terminally clean bounded MySQL pool evidence.
            int(pool.get("timeout_count", 0)) == 0  # Refuse checkout timeouts.
            and int(pool.get("connector_error", 0)) == 0  # Refuse connector failures.
            and int(pool.get("in_use", 0)) == 0  # Require every physical lease to return.
            and int(pool.get("waiting", 0)) == 0  # Require every waiter to resolve.
            and int(pool.get("physical_created", 0)) <= int(pool.get("capacity", 0))  # Preserve fixed-cardinality capacity.
        ),
        "pool_preflight": bool(pool_preflight)  # Require one exact-source Package B evidence packet.
        and [row.get("concurrency") for row in pool_preflight.get("measurements", [])] == [1, 2, 4, 8]  # Require all governed levels in order.
        and all(int(row.get("errors", 1)) == 0 for row in pool_preflight.get("measurements", []))  # Refuse measurement errors.
        and int(pool_preflight.get("pool", {}).get("timeout_count", 1)) == 0  # Refuse preflight checkout timeouts.
        and int(pool_preflight.get("pool", {}).get("connector_error", 1)) == 0,  # Refuse preflight connector failures.
    }
    # Build one secret-safe exact-source aggregate artifact.
    report = {
        "status": "PASS" if all(gates.values()) else "FAIL",  # Publish one fail-closed terminal outcome.
        "qualification": {
            "test_id": "BR-CONCURRENT-138-001",  # Bind the permanent hosted browser identity.
            "requirements": list(REQUIREMENT_IDS),  # Bind the complete permanent requirement set.
            "source_commit": source_commit,  # Bind evidence to the exact qualified source.
            "user_count": USER_COUNT,  # Publish only the fixed synthetic population.
            "registered_game_count": len(GAME_IDS),  # Publish the aggregate catalog size.
            "minimum_users_per_game": MINIMUM_USERS_PER_GAME,  # Publish the owner-selected coverage floor.
        },
        "gates": gates,  # Preserve every independent acceptance gate.
        "counts": {
            "setup_admission_limit": SETUP_ADMISSION_LIMIT,  # Publish the bounded pre-barrier policy.
            "peak_setup": counters["peak_setup"],  # Publish only aggregate observed setup concurrency.
            "barrier_ready": barrier.ready,  # Publish aggregate synchronized-gate population.
            "login_success": sum(bool(row.get("login_ok")) for row in results),  # Publish aggregate authentication success.
            "gameplay_success": sum(bool(row.get("gameplay_ok")) for row in results),  # Publish aggregate gameplay success.
            "contexts_closed": sum(bool(row.get("context_closed")) for row in results),  # Publish aggregate context cleanup.
            "peak_gameplay": counters["peak_gameplay"],  # Publish peak simultaneous post-login gameplay.
        },
        "assigned_by_game": dict(sorted(assigned_by_game.items())),  # Publish aggregate deterministic coverage only.
        "successful_by_game": dict(sorted(successful_by_game.items())),  # Publish aggregate successful coverage only.
        "latency": {"login": latency_summary(login_latencies), "gameplay": latency_summary(play_latencies)},  # Publish bounded latency summaries.
        "browser_diagnostics": {name: dict(counter.most_common()) for name, counter in diagnostics.items()},  # Publish grouped safe failures.
        "failure_counts": dict(failure_counts.most_common()),  # Publish bounded safe exception signatures.
        "failure_attribution": [
            {"game_id": game_id, "phase": phase, "action_state": action_state, "error": error, "count": count}  # Publish one aggregate public attribution row.
            for (game_id, phase, action_state, error), count in sorted(failure_attribution_counts.items())  # Preserve deterministic public ordering.
        ],  # Publish exact public game/phase/state/error attribution without user-level rows.
        "phase_counts": {
            "completed": {phase: completed_phase_counts.get(phase, 0) for phase in FORMAL_PHASES},  # Publish fixed completion counts.
            "failed": {phase: failed_phase_counts.get(phase, 0) for phase in FORMAL_FAILURE_PHASES},  # Publish fixed failure counts.
        },
        "action_state_counts": {  # Publish fixed action-state totals beside the existing phase totals.
            "completed": {state: completed_action_state_counts.get(state, 0) for state in FORMAL_ACTION_STATES},  # Publish fixed action-state completion counts.
            "failed": {state: failed_action_state_counts.get(state, 0) for state in FORMAL_FAILURE_ACTION_STATES},  # Publish fixed terminal action-state failures.
        },
        "isolation": isolation,  # Publish aggregate wallet and ledger invariants.
        "pool": pool,  # Publish fixed low-cardinality pool evidence.
        "pool_preflight": pool_preflight,  # Preserve the exact-source 1/2/4/8 packet.
        "elapsed_seconds": round(float(elapsed_seconds), 3),  # Publish bounded wall time.
    }
    # Return the terminal aggregate without user-level rows.
    return report


# Validate the explicit disposable boundary before imports create runtime state.
def validate_runtime_boundary():
    # Require one exact opt-in marker for this resource-intensive local-only profile.
    if os.environ.get("CASINO_225_DISPOSABLE") != "1":
        # Fail before source copies, listeners, accounts, or browsers.
        raise RuntimeError("CASINO_225_DISPOSABLE=1 is required")
    # Resolve the environment-selected data root loaded by Casino configuration.
    from casino.config import DATA_DIR

    # Resolve the source checkout and configured data root for containment checks.
    source = ui_50000.ROOT.resolve()
    # Resolve the selected test-owned data root.
    data_root = DATA_DIR.resolve()
    # Reject the repository, its normal data tree, or any child path as a qualification target.
    if data_root == source or source in data_root.parents:
        # Require disposable data outside the checkout before any state mutation.
        raise RuntimeError("qualification data root must be outside the source checkout")
    # Reject absent explicit environment selection even if a caller's current directory changed defaults.
    if not os.environ.get("CASINO_DATA_DIR", "").strip():
        # Keep local developer data outside the harness boundary.
        raise RuntimeError("CASINO_DATA_DIR must select an external disposable directory")
    # Return the verified external data root for exact cleanup.
    return data_root


# Run the complete formal profile and always clean every test-owned resource.
async def run_qualification(args):
    # Validate catalog arithmetic before opening any resource.
    assignments = build_assignment_plan()
    # Validate the explicit external disposable data boundary.
    data_root = validate_runtime_boundary()
    # Freeze exact clean source provenance before qualification.
    source_commit = ui_50000.resolve_source_commit()
    # Require the same exact source's completed Package B MySQL preflight before any listener opens.
    pool_preflight = load_pool_preflight(args.pool_preflight, source_commit)
    # Start the terminal timer before setup begins.
    started_at = time.perf_counter()
    # Track exact server, thread, browser, and report resources.
    server = None
    # Start without a server thread.
    server_thread = None
    # Start without an API evidence client.
    client = None
    # Start without a browser process.
    browser = None
    # Start without task results.
    results = []
    # Track whether this invocation created the external data root.
    data_root_created = False
    # Start fail-closed listener cleanup evidence.
    listener_cleanup = {"closed": False}
    # Build the exact synchronized pre-login boundary.
    barrier = StartBarrier(USER_COUNT)
    # Bound only pre-barrier context and shell setup while preserving all 138 independent waiting contexts.
    setup_admission = asyncio.Semaphore(SETUP_ADMISSION_LIMIT)
    # Track active and peak setup plus gameplay with aggregate counters only.
    counters = {"active_setup": 0, "peak_setup": 0, "active_gameplay": 0, "peak_gameplay": 0}
    # Serialize setup and gameplay counter mutations.
    counter_lock = asyncio.Lock()
    # Start without provisioned credential-bearing in-memory users.
    users = []
    # Preserve no isolation evidence until every task is terminal.
    isolation = {}
    # Preserve no pool snapshot until every request has completed.
    pool = {"available": False}
    # Start protected resource ownership so every failure path closes exactly.
    try:
        # Create the external disposable data directory only after all preflight checks pass.
        data_root.mkdir(parents=True, exist_ok=False)
        # Record exact ownership only after creation succeeds.
        data_root_created = True
        # Start one shared loopback-only runtime in this process.
        server, server_thread, client = start_loopback_server()
        # Reset only the freshly created disposable runtime and restore setup authentication.
        client.call("/api/v1/casino/reset", "POST", {})
        # Re-establish the setup-only Admin session after reset.
        client.login_default_user()
        # Provision exactly 138 distinct synthetic accounts before opening browser contexts.
        for assignment in assignments:
            # Derive the same deterministic locale used by the browser task.
            locale = "en-US" if assignment["user_index"] % 2 == 0 else "ru-RU"
            # Keep each credential-bearing user only in process memory.
            users.append(create_synthetic_user(client, assignment["user_index"], locale))
        # Import Playwright only after disposable setup and arithmetic gates pass.
        from playwright.async_api import async_playwright

        # Own the complete browser driver lifecycle.
        async with async_playwright() as playwright:
            # Launch one process containing 138 independent browser contexts.
            browser = await playwright.chromium.launch(headless=not args.headed)
            # Start one task per deterministic assignment and unique synthetic account.
            tasks = [
                asyncio.create_task(run_user(browser, client, assignment, user, barrier, setup_admission, counters, counter_lock))
                for assignment, user in zip(assignments, users)
            ]
            # Start without a barrier failure so every task can still be awaited.
            barrier_error = None
            # Wait for every context to reach the rendered login gate.
            try:
                # Bound the synchronized setup phase.
                await asyncio.wait_for(barrier.all_ready.wait(), timeout=args.barrier_timeout)
            # Preserve the bounded setup failure only after every context receives a release.
            except Exception as error:
                # Retain the controller exception without interrupting task cleanup.
                barrier_error = error
            # Release waiting contexts even when one setup task failed or timed out.
            finally:
                # Let all terminal task cleanup paths progress.
                barrier.release.set()
            # Materialize every terminal sanitized result.
            results = await asyncio.gather(*tasks)
            # Surface the original barrier failure after every task is terminal.
            if barrier_error is not None:
                # Keep a partial population from being mistaken for a completed synchronized run.
                raise barrier_error
            # Close the shared Chromium process after all contexts have closed.
            await browser.close()
            # Clear the local handle so the outer cleanup does not close it twice.
            browser = None
        # Collect canonical wallet, ledger, and settlement isolation evidence after browser activity stops.
        isolation = collect_isolation_evidence(client, users, results)
        # Capture final fixed-cardinality Package B pool metrics from the process that served the load.
        pool = pool_snapshot()
    # Preserve a terminal aggregate even when setup or controller logic fails.
    except Exception as error:
        # Record one controller-level failure without private paths or credentials.
        results.append(
            {
                "game_id": "controller",
                "barrier_ready": False,
                "login_ok": False,
                "gameplay_ok": False,
                "context_closed": browser is None,
                "error": safe_error(error),
                "browser_diagnostics": {"console_errors": {}, "page_errors": {}, "http_failures": {}},
            }
        )
        # Release any tasks still waiting at the barrier.
        barrier.release.set()
    # Always close browser, listener, provider, and external data resources.
    finally:
        # Close a browser left alive by controller failure.
        if browser is not None:
            # Release all surviving test-owned contexts and browser children.
            await browser.close()
        # Stop and verify the exact test-owned listener.
        if server is not None and server_thread is not None:
            # Preserve closure evidence for the terminal report.
            listener_cleanup = stop_loopback_server(server, server_thread)
        # Close process-local MySQL idle connections when the selected provider owns them.
        try:
            # Import storage only after runtime setup was attempted.
            from casino.core import storage

            # Resolve the currently cached disposable provider.
            provider = storage.get_storage_provider()
            # Resolve its optional terminal pool cleanup seam.
            close_pool = getattr(provider, "close_pool", None)
            # Close idle physical sessions when applicable.
            if callable(close_pool):
                # Release all process-owned MySQL connections.
                close_pool()
        # Ignore absent provider state after an early boundary failure.
        except Exception:
            # Preserve the primary qualification failure while external cleanup continues.
            pass
        # Remove only the exact external directory created by this harness.
        if data_root_created and data_root.exists():
            # Delete synthetic accounts, ledgers, sessions, and game state after listener closure.
            shutil.rmtree(data_root)
    # Fill absent isolation evidence with explicit failing zeros.
    if not isolation:
        # Keep the terminal schema stable after setup failures.
        isolation = {
            "unique_player_count": 0,
            "duplicate_player_id_count": 0,
            "matching_player_count": 0,
            "nonnegative_balance_count": 0,
            "users_with_gameplay_ledger": 0,
            "wager_evidence_required": 0,  # Preserve the terminal schema after early failure.
            "wager_evidence_satisfied": 0,  # Preserve missing wager proof explicitly.
            "non_wager_actions": 0,  # Preserve absent no-wager evidence explicitly.
            "non_wager_actions_with_ledger": 0,  # Preserve the no-wager anomaly field.
            "classified_gameplay_actions": 0,  # Preserve absent action classification explicitly.
            "duplicate_ledger_id_count": 0,
            "duplicate_action_key_count": 0,
        }
    # Build the aggregate after all cleanup has completed.
    report = aggregate_results(
        assignments,
        results,
        barrier,
        counters,
        isolation,
        pool,
        pool_preflight,
        source_commit,
        time.perf_counter() - started_at,
    )
    # Add the exact listener cleanup gate after aggregate construction.
    report["listener_cleanup"] = listener_cleanup
    # Require verified listener closure for terminal PASS.
    report["gates"]["listener_cleanup"] = listener_cleanup.get("closed") is True
    # Recalculate status after the cleanup gate is present.
    report["status"] = "PASS" if all(report["gates"].values()) else "FAIL"
    # Write the terminal JSON report outside the source checkout.
    ui_50000.write_json(Path(args.report).expanduser().resolve(), report)
    # Emit only concise public aggregate counts.
    print(
        f"BROWSER138 {report['status']} "
        f"barrier={report['counts']['barrier_ready']}/{USER_COUNT} "
        f"login={report['counts']['login_success']}/{USER_COUNT} "
        f"gameplay={report['counts']['gameplay_success']}/{USER_COUNT} "
        f"closed={report['counts']['contexts_closed']}/{USER_COUNT}",
        flush=True,
    )
    # Return standard success only after every acceptance and cleanup gate passes.
    return 0 if report["status"] == "PASS" else 1


# Parse the immutable formal profile without allowing acceptance counts to drift.
def parse_args(argv=None):
    # Describe the exact issue-owned qualification.
    parser = argparse.ArgumentParser(description="Run exactly 138 synchronized independent Casino browser users.")
    # Accept only an external terminal report path.
    parser.add_argument(
        "--report",
        default=str(Path(tempfile.gettempdir()) / "casino-browser-138.json"),
        help="External path for the sanitized aggregate JSON report.",
    )
    # Bound pre-login barrier setup while preserving the exact population.
    parser.add_argument(
        "--barrier-timeout",
        type=int,
        default=BARRIER_TIMEOUT_SECONDS,
        help="Seconds to wait for all 138 rendered login gates.",
    )
    # Require exact-source Package B 1/2/4/8 evidence before the browser run.
    parser.add_argument(
        "--pool-preflight",
        required=True,
        help="External JSON artifact from the exact-source disposable MySQL pool preflight.",
    )
    # Allow an explicit visible local debugging run without changing formal semantics.
    parser.add_argument("--headed", action="store_true", help="Show the test-owned browser for explicit debugging.")
    # Parse the caller arguments.
    args = parser.parse_args(argv)
    # Reject nonpositive or unreasonably long barrier waits.
    if not 1 <= args.barrier_timeout <= 600:
        # Keep setup bounded and actionable.
        parser.error("--barrier-timeout must be between 1 and 600 seconds")
    # Reject a report path inside the source checkout.
    report_path = Path(args.report).expanduser().resolve()
    # Compare the report target against the immutable source root.
    if report_path == ui_50000.ROOT.resolve() or ui_50000.ROOT.resolve() in report_path.parents:
        # Keep formal evidence out of source-controlled files.
        parser.error("--report must be outside the source checkout")
    # Resolve the preflight path for the same external-artifact safety boundary.
    preflight_path = Path(args.pool_preflight).expanduser().resolve()
    # Reject generated preflight evidence inside the source checkout.
    if preflight_path == ui_50000.ROOT.resolve() or ui_50000.ROOT.resolve() in preflight_path.parents:
        # Keep measurement evidence external and immutable for the run.
        parser.error("--pool-preflight must be outside the source checkout")
    # Return the validated immutable profile.
    return args


# Run the formal profile from the command line.
def main(argv=None):
    # Parse the caller-owned output and timeout controls.
    args = parse_args(argv)
    # Start protected controller execution so CLI failures remain path- and credential-safe.
    try:
        # Execute the asynchronous browser controller.
        return asyncio.run(run_qualification(args))
    # Convert pre-resource planning and boundary failures to one bounded public diagnostic.
    except Exception as error:
        # Emit no traceback, private path, credential, token, cookie, PID, or port.
        print(f"BROWSER138 FAIL controller={safe_error(error)}", flush=True)
        # Return standard failure for the explicit workflow.
        return 1


# Preserve standard CLI exit behavior.
if __name__ == "__main__":
    # Exit nonzero on any qualification or cleanup failure.
    raise SystemExit(main())
