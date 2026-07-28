#!/usr/bin/env python3
"""Run the issue #225 exact-138 real-browser qualification on a disposable loopback runtime."""

import argparse  # Parse the immutable qualification profile and artifact locations.
import asyncio  # Coordinate independent browser contexts and the synchronized start barrier.
import json  # Persist only sanitized aggregate qualification evidence.
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
# Bind the formal report to permanent requirement and browser-test identities.
REQUIREMENT_IDS = ("AUTH-001", "AUTH-002", "SESSION-001", "SESSION-005", "TEST-039", "TEST-042", "TEST-142", "CORE-021")
# Reuse canonical game order so catalog growth changes the plan deterministically.
GAME_IDS = tuple(game["id"] for game in GAMES)


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
    server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
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


# Run one independent browser context from the rendered login gate through one complete game play.
async def run_user(browser, client, assignment, user, barrier, counters, counter_lock):
    # Derive one deterministic locale without introducing a user-visible allowlist.
    locale = "en-US" if assignment["user_index"] % 2 == 0 else "ru-RU"
    # Start without browser resources so partial setup remains cleanable.
    context = None
    # Start one fail-closed aggregate result without account identifiers.
    result = {
        "game_id": assignment["game_id"],
        "barrier_ready": False,
        "login_ok": False,
        "gameplay_ok": False,
        "context_closed": False,
    }
    # Collect only grouped credential-free browser diagnostics for this context.
    diagnostics = {"console_errors": Counter(), "page_errors": Counter(), "http_failures": Counter()}
    # Start protected browser work so cookies and session storage always close.
    try:
        # Create one independent cookie, cache, and session-storage boundary.
        context = await browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        # Open one page owned only by this synthetic account.
        page = await context.new_page()
        # Attach grouped console, page, and protected-request failure observers.
        ui_50000.attach_page_diagnostics(page, diagnostics)
        # Navigate to the public shell before the synchronized release.
        await page.goto(client.base_url, wait_until="domcontentloaded", timeout=ui_50000.SETUP_TIMEOUT_MS)
        # Require the rendered login gate before counting this context at the barrier.
        await page.get_by_test_id("login-gate").wait_for(state="visible", timeout=ui_50000.SETUP_TIMEOUT_MS)
        # Mark this exact independent context ready.
        result["barrier_ready"] = True
        # Wait until all 138 contexts are ready and the controller releases them together.
        await barrier.wait()
        # Start aggregate login timing immediately after the synchronized release.
        login_started = time.perf_counter()
        # Track rendered login controls without persisting individual control histories.
        activated_counts = Counter()
        # Authenticate through the real localized form.
        await ui_50000.login_through_ui(page, client.base_url, user, locale, activated_counts)
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
            # Navigate through the catalog-owned UI route.
            await ui_50000.navigate_to_game(page, assignment["game_id"], activated_counts, assignment["user_index"])
            # Complete one game-owned action through rendered controls.
            await ui_50000.play_game_ui(page, assignment["game_id"], assignment["user_index"], seen_counts, activated_counts)
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
    # Always destroy this independent browser context.
    finally:
        # Close cookies, cache, pages, and session storage when context creation succeeded.
        if context is not None:
            # Release the exact test-owned browser context.
            await context.close()
            # Record successful context cleanup.
            result["context_closed"] = True
        # Convert diagnostic counters to deterministic JSON mappings.
        result["browser_diagnostics"] = {name: dict(counter.most_common()) for name, counter in diagnostics.items()}
    # Return one sanitized task result without account identifiers.
    return result


# Validate post-run account and ledger isolation through setup-only Admin APIs.
def collect_isolation_evidence(client, users):
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
    # Inspect every synthetic account sequentially after browser activity has stopped.
    for user in users:
        # Read only this account's bounded Admin state.
        state = client.call(f"/api/v2/admin/users/{user['user_id']}/state")
        # Count the canonical player binding without persisting either identity.
        matching_players += int(state["player_id"] == user["player_id"])
        # Count nonnegative synthetic wallet state.
        nonnegative_balances += int(float(state["token_balance"]) >= 0)
        # Read this player's bounded ledger through the setup-only Admin evidence API.
        rows = client.call(f"/api/v1/admin/ledger?player_id={user['player_id']}&limit=100")["ledger"]
        # Keep immutable ledger identifiers in memory only for duplicate detection.
        ledger_ids.extend(str(row.get("ledger_id") or "") for row in rows if row.get("ledger_id"))
        # Exclude the one setup grant before requiring gameplay ledger evidence.
        gameplay_rows = [row for row in rows if row.get("transaction_type") != "ADMIN_TOKEN_GRANT"]
        # Count users with at least one game-owned ledger movement.
        users_with_gameplay_ledger += int(bool(gameplay_rows))
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
        "exact_users": len(assignments) == USER_COUNT and len(results) == USER_COUNT,
        "barrier": barrier.ready == USER_COUNT and barrier.peak_ready == USER_COUNT,
        "authentication": sum(bool(row.get("login_ok")) for row in results) == USER_COUNT,
        "gameplay": sum(bool(row.get("gameplay_ok")) for row in results) == USER_COUNT,
        "catalog_coverage": set(assigned_by_game) == set(GAME_IDS)
        and min(assigned_by_game.values(), default=0) >= MINIMUM_USERS_PER_GAME
        and min(successful_by_game.values(), default=0) >= MINIMUM_USERS_PER_GAME,
        "browser_diagnostics": not any(diagnostics[name] for name in diagnostics),
        "isolation": isolation["unique_player_count"] == USER_COUNT
        and isolation["duplicate_player_id_count"] == 0
        and isolation["matching_player_count"] == USER_COUNT
        and isolation["nonnegative_balance_count"] == USER_COUNT
        and isolation["users_with_gameplay_ledger"] == USER_COUNT
        and isolation["duplicate_ledger_id_count"] == 0
        and isolation["duplicate_action_key_count"] == 0,
        "context_cleanup": sum(bool(row.get("context_closed")) for row in results) == USER_COUNT,
        "pool": not pool.get("available")
        or (
            int(pool.get("timeout_count", 0)) == 0
            and int(pool.get("connector_error", 0)) == 0
            and int(pool.get("in_use", 0)) == 0
            and int(pool.get("waiting", 0)) == 0
            and int(pool.get("physical_created", 0)) <= int(pool.get("capacity", 0))
        ),
        "pool_preflight": bool(pool_preflight)
        and [row.get("concurrency") for row in pool_preflight.get("measurements", [])] == [1, 2, 4, 8]
        and all(int(row.get("errors", 1)) == 0 for row in pool_preflight.get("measurements", []))
        and int(pool_preflight.get("pool", {}).get("timeout_count", 1)) == 0
        and int(pool_preflight.get("pool", {}).get("connector_error", 1)) == 0,
    }
    # Build one secret-safe exact-source aggregate artifact.
    report = {
        "status": "PASS" if all(gates.values()) else "FAIL",
        "qualification": {
            "test_id": "BR-CONCURRENT-138-001",
            "requirements": list(REQUIREMENT_IDS),
            "source_commit": source_commit,
            "user_count": USER_COUNT,
            "registered_game_count": len(GAME_IDS),
            "minimum_users_per_game": MINIMUM_USERS_PER_GAME,
        },
        "gates": gates,
        "counts": {
            "barrier_ready": barrier.ready,
            "login_success": sum(bool(row.get("login_ok")) for row in results),
            "gameplay_success": sum(bool(row.get("gameplay_ok")) for row in results),
            "contexts_closed": sum(bool(row.get("context_closed")) for row in results),
            "peak_gameplay": counters["peak_gameplay"],
        },
        "assigned_by_game": dict(sorted(assigned_by_game.items())),
        "successful_by_game": dict(sorted(successful_by_game.items())),
        "latency": {"login": latency_summary(login_latencies), "gameplay": latency_summary(play_latencies)},
        "browser_diagnostics": {name: dict(counter.most_common()) for name, counter in diagnostics.items()},
        "failure_counts": dict(failure_counts.most_common()),
        "isolation": isolation,
        "pool": pool,
        "pool_preflight": pool_preflight,
        "elapsed_seconds": round(float(elapsed_seconds), 3),
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
    # Track active and peak gameplay with aggregate counters only.
    counters = {"active_gameplay": 0, "peak_gameplay": 0}
    # Serialize active-gameplay counter mutations.
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
                asyncio.create_task(run_user(browser, client, assignment, user, barrier, counters, counter_lock))
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
        isolation = collect_isolation_evidence(client, users)
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
