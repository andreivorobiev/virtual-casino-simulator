# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Run the TEST-251 authenticated-session load smoke through production Gunicorn."""

# Import argument parsing for the explicit disposable provider, population, and report path.
import argparse
# Import bounded concurrent futures for synchronized authenticated game actions.
import concurrent.futures
# Import JSON serialization for one aggregate exact-source report.
import json
# Import operating-system configuration and platform detection for fail-closed qualification gates.
import os
# Import paths for repository containment and external report validation.
from pathlib import Path
# Import disposable external runtime roots for state and logs.
import tempfile
# Import thread barriers so every authenticated session starts its round together.
import threading
# Import aggregate elapsed-time measurement without per-user timing rows.
import time

# Reuse the accepted production listener, request, and cleanup helpers rather than another serving stack.
from tests import production_service_smoke
# Reuse the existing shared-MySQL synthetic Admin so sequential qualification children bootstrap idempotently.
from tests import request_latency_benchmark
# Reuse the exact-clean-checkout provenance gate shared by hosted qualification tools.
from tests import ui_50000

# Resolve repository containment from this tracked test module.
ROOT = Path(__file__).resolve().parents[1]
# Require one exact opt-in before any disposable listener or account is created.
DISPOSABLE_MARKER = "CASINO_1040_DISPOSABLE"
# Bound ordinary pull-request smoke to a few dozen independent sessions.
CI_USERS = 32
# Bind formal acceptance to the issue's exact synchronized population.
FORMAL_USERS = 100
# Bound routine authentication fan-out below the shared process thread ceiling before round synchronization.
CI_LOGIN_WORKERS = 8
# Permit one login or round to wait behind the reviewed 100-to-32 request queue without becoming unbounded.
LOAD_REQUEST_TIMEOUT_SECONDS = 120
# Permit every authenticated session to reach the exact post-login barrier on a two-core hosted runner.
LOAD_BARRIER_TIMEOUT_SECONDS = 180
# Name every administrator or migrator capability forbidden in the production-stack child.
MYSQL_CHILD_CAPABILITY_KEYS = (
    "CASINO_MYSQL_TEST_ADMIN_USER",  # Withhold the disposable administrator identity.
    "CASINO_MYSQL_TEST_ADMIN_PASSWORD",  # Withhold the disposable administrator secret.
    "CASINO_MYSQL_MIGRATION_USER",  # Withhold the schema migrator identity.
    "CASINO_MYSQL_MIGRATION_PASSWORD",  # Withhold the schema migrator secret.
    "CASINO_MYSQL_MIGRATION_DATABASE",  # Withhold the migrator-owned target selector.
    "CASINO_MYSQL_MIGRATION_TARGET_BINDING_KEY",  # Withhold private target-binding material.
)


# Raise one value-free category for every fail-closed qualification refusal.
class GunicornLoadSmokeError(RuntimeError):
    # Keep the exception behavior identical to the standard runtime category.
    pass


# Parse the explicit provider, exact population, and caller-external report destination.
def parse_args():
    # Describe the production-stack-only concurrency gate.
    parser = argparse.ArgumentParser(description="Run an isolated authenticated load smoke through Gunicorn.")
    # Require a named provider so JSON and disposable MySQL evidence cannot be confused.
    parser.add_argument("--provider", choices=("json", "mysql"), required=True)
    # Permit only the ordinary CI population or the exact formal qualification population.
    parser.add_argument("--users", type=int, choices=(CI_USERS, FORMAL_USERS), required=True)
    # Require one explicit aggregate report destination outside the source checkout.
    parser.add_argument("--report", type=Path, required=True)
    # Return the fully parsed namespace without opening a listener.
    return parser.parse_args()


# Require the report destination and provider authorization before process construction.
def validate_boundaries(provider: str, users: int, report_path: Path) -> Path:
    # Require the exact issue-owned disposable marker rather than any truthy value.
    if os.environ.get(DISPOSABLE_MARKER) != "1":
        # Refuse unmarked execution before state, account, or listener allocation.
        raise GunicornLoadSmokeError("load smoke requires the disposable marker")
    # Keep the population at one of the two reviewed qualification levels.
    if users not in {CI_USERS, FORMAL_USERS}:
        # Reject arbitrary fan-out before worker construction.
        raise GunicornLoadSmokeError("load smoke population is unsupported")
    # Require the disposable MySQL service marker before any database-backed child starts.
    if provider == "mysql" and os.environ.get("CASINO_MYSQL_DISPOSABLE_TEST") != "1":
        # Refuse an unclassified MySQL target without reflecting configuration.
        raise GunicornLoadSmokeError("MySQL load smoke requires the disposable database marker")
    # Resolve the caller-selected aggregate destination without creating it.
    resolved = report_path.expanduser().resolve()
    # Refuse reports inside the source checkout so qualification cannot dirty exact provenance.
    try:
        # Test containment against the immutable source root.
        resolved.relative_to(ROOT)
    # Accept only paths outside the repository.
    except ValueError:
        # Return the validated external report destination.
        return resolved
    # Fail when containment succeeded.
    raise GunicornLoadSmokeError("load smoke report must be outside the repository")


# Build one exact production environment over a disposable external runtime root.
def service_environment(runtime_root: Path, port: int, provider: str) -> dict:
    # Start from the accepted production-service smoke environment and its private credentials.
    environment = production_service_smoke.service_environment(runtime_root, port)
    # Select the explicitly requested disposable storage provider.
    environment["CASINO_STORAGE_PROVIDER"] = provider
    # Reuse the prior MySQL qualification Admin so the sole default player is never rebound to a second identity.
    environment["CASINO_BOOTSTRAP_ADMIN_EMAIL"] = request_latency_benchmark.SYNTHETIC_EMAIL
    # Reuse its synthetic credential because an existing bootstrap identity is intentionally left unchanged.
    environment["CASINO_BOOTSTRAP_ADMIN_PASSWORD"] = request_latency_benchmark.SYNTHETIC_PASSWORD
    # Reuse the token-digest namespace because the preceding benchmark leaves authenticated state in MySQL.
    environment["CASINO_TOKEN_DIGEST_KEY"] = request_latency_benchmark.SYNTHETIC_TOKEN_DIGEST_KEY
    # Reuse the mail-digest namespace so the preceding benchmark's persisted Admin remains discoverable.
    environment["CASINO_MAIL_DIGEST_KEY"] = request_latency_benchmark.SYNTHETIC_MAIL_DIGEST_KEY
    # Pin the reviewed single-process topology for coherent in-worker state ownership.
    environment["CASINO_GUNICORN_WORKERS"] = "1"
    # Use thirty-two request threads so the 100-user profile measures a bounded server queue.
    environment["CASINO_GUNICORN_THREADS"] = "32"
    # Pin the reviewed physical MySQL ceiling independently from request threads.
    environment["CASINO_MYSQL_POOL_SIZE"] = "16"
    # Permit the formal 32-to-16 request queue to drain within the documented bounded checkout range.
    environment["CASINO_MYSQL_POOL_WAIT_MS"] = "10000"
    # Permit the fixed synthetic population behind one loopback client without changing production defaults.
    environment["CASINO_RATE_LIMIT_REQUESTS"] = "10000"
    # Keep the synthetic allowance inside one fixed bounded window.
    environment["CASINO_RATE_LIMIT_WINDOW_SECONDS"] = "60"
    # Supply a valid synthetic monitor verifier so every production-only auth path is configured.
    environment["CASINO_EDGE_MONITOR_TOKEN_SHA256"] = "e" * 64
    # Remove every administrator and migrator capability before the Gunicorn worker imports Casino.
    for key in MYSQL_CHILD_CAPABILITY_KEYS:
        # Preserve only the already guarded runtime DML identity and loopback endpoint facts.
        environment.pop(key, None)
    # Return the child-only mapping; existing disposable MySQL target values remain inherited.
    return environment


# Provision one reserved-domain player through the documented Admin API.
def create_user(base_url: str, admin_token: str, admin_csrf: str, index: int) -> dict:
    # Derive a deterministic synthetic email that cannot receive real mail.
    email = f"gunicorn-load-{index:03d}@example.invalid"
    # Derive an in-memory password unique to this disposable account.
    password = f"GunicornLoad-{index:03d}-Synthetic!"
    # Create the funded, terms-accepted player before concurrent login begins.
    created = production_service_smoke.api_request(
        base_url,
        "/api/v1/admin/users",
        "POST",
        {
            "email": email,
            "password": password,
            "display_name": f"Gunicorn Load {index:03d}",
            "initial_tokens": 100,
            "terms_accepted": True,
            "language": "en-US",
            "format_locale": "en-US",
        },
        admin_token,
        admin_csrf,
    )
    # Require a linked player without retaining its identifier in terminal evidence.
    if created.get("ok") is not True or not created.get("data", {}).get("user", {}).get("player_id"):
        # Stop with one value-free setup category.
        raise GunicornLoadSmokeError("synthetic account provisioning failed")
    # Return credentials only to the in-memory worker plan.
    return {"email": email, "password": password}


# Authenticate one account and retain only the two proofs needed by its disposable round.
def authenticate_user(base_url: str, user: dict) -> dict:
    # Obtain a fresh anonymous double-submit proof for this independent session.
    bootstrap = production_service_smoke.bootstrap_csrf(base_url, timeout_seconds=LOAD_REQUEST_TIMEOUT_SECONDS)
    # Authenticate through the production listener with the account's own proof.
    login = production_service_smoke.api_request(base_url, "/api/v2/auth/login", "POST", {"email": user["email"], "password": user["password"]}, csrf=bootstrap, timeout_seconds=LOAD_REQUEST_TIMEOUT_SECONDS)
    # Read the standard successful session object without publishing its authority.
    session = login.get("data", {}).get("session", {}) if login.get("ok") is True else {}
    # Require both bearer and CSRF proofs before joining the synchronized action population.
    if not session.get("token") or not session.get("csrf_token"):
        # Use one fixed worker category with no account detail.
        raise GunicornLoadSmokeError("synthetic session authentication failed")
    # Return only the child-local authorization values required by the action worker.
    return {"token": session["token"], "csrf_token": session["csrf_token"]}


# Wait for every authenticated session and execute one idempotent Boule round.
def run_authenticated_round(base_url: str, session: dict, index: int, barrier: threading.Barrier) -> bool:
    # Wait until all independent authenticated sessions are ready for their one game round.
    barrier.wait(timeout=LOAD_BARRIER_TIMEOUT_SECONDS)
    # Execute one bounded paid action through the public game route.
    result = production_service_smoke.api_request(
        base_url,
        "/api/v1/games/boule/spins",
        "POST",
        {"request_id": f"gunicorn-load-{index:03d}", "bet": "even", "stake": 1},
        session["token"],
        session["csrf_token"],
        LOAD_REQUEST_TIMEOUT_SECONDS,
    )
    # Require the first committed response rather than a failure or replay.
    if result.get("ok") is not True or result.get("data", {}).get("replayed") is not False:
        # Keep game failure independent from response content.
        raise GunicornLoadSmokeError("synthetic game round failed")
    # Return one aggregate-compatible completion marker.
    return True


# Authenticate the complete routine population under one bounded login concurrency ceiling.
def authenticate_population(base_url: str, plan: list[dict]) -> list[dict]:
    # Use a small fixed login cohort so authentication failures surface before the round barrier.
    with concurrent.futures.ThreadPoolExecutor(max_workers=CI_LOGIN_WORKERS) as executor:
        # Submit every independent login while preserving deterministic result order.
        futures = [executor.submit(authenticate_user, base_url, user) for user in plan]
        # Materialize every session before any game worker can occupy the synchronized barrier.
        return [future.result() for future in futures]


# Validate the final Admin pool telemetry variant for the selected provider.
def validate_pool_telemetry(provider: str, payload: dict) -> dict:
    # Read the exact public pool object from the successful Admin heartbeat.
    pool = payload.get("data", {}).get("storage_pool", {}) if payload.get("ok") is True else {}
    # JSON must publish only the explicit not-applicable variant.
    if provider == "json":
        # Reject fabricated MySQL metrics in the provider-neutral run.
        if pool != {"available": False}:
            # Fail with no response detail.
            raise GunicornLoadSmokeError("JSON pool telemetry was not unavailable")
        # Return a fresh copy for aggregate evidence.
        return {"available": False}
    # Require the exact available MySQL key set.
    expected = {"available", "capacity", "in_use", "idle", "waiting", "saturation_count", "timeout_count"}
    # Reject missing or expanded diagnostic dimensions.
    if type(pool) is not dict or set(pool) != expected or pool.get("available") is not True:
        # Fail without serializing provider output.
        raise GunicornLoadSmokeError("MySQL pool telemetry shape failed")
    # Require the configured ceiling and clean terminal gauges.
    if pool.get("capacity") != 16 or pool.get("in_use") != 0 or pool.get("waiting") != 0 or pool.get("timeout_count") != 0:
        # Fail on saturation damage or leaked requests without reporting values.
        raise GunicornLoadSmokeError("MySQL pool terminal state failed")
    # Rebuild only allowlisted low-cardinality fields.
    return {name: pool[name] for name in ("available", "capacity", "in_use", "idle", "waiting", "saturation_count", "timeout_count")}


# Persist one sanitized report atomically after every process and listener has closed.
def write_report(path: Path, report: dict) -> None:
    # Create only the caller-owned external parent after successful qualification.
    path.parent.mkdir(parents=True, exist_ok=True)
    # Select a same-directory temporary file for atomic replacement.
    temporary = path.with_name(path.name + ".tmp")
    # Write stable sorted JSON without account, token, path, target, or timing samples.
    temporary.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    # Atomically publish the complete terminal report.
    temporary.replace(path)


# Run one exact-source disposable qualification and return its aggregate report.
def run(provider: str, users: int, report_path: Path) -> dict:
    # Validate every caller-controlled boundary before provenance or resource allocation.
    output = validate_boundaries(provider, users, report_path)
    # Freeze a clean exact commit so hosted reports cannot be replayed across sources.
    source_commit = ui_50000.resolve_source_commit()
    # Keep the server handle unset for guaranteed single-process cleanup.
    process = None
    # Track the exact private listener for closure proof.
    port = production_service_smoke.free_port()
    # Allocate one complete external runtime that disappears after terminal cleanup.
    with tempfile.TemporaryDirectory(prefix="casino-gunicorn-load-") as temporary:
        # Resolve only the disposable state/log root used by the production adapter.
        runtime_root = Path(temporary)
        # Build the fixed loopback URL without placing it in evidence.
        base_url = f"http://127.0.0.1:{port}"
        # Build the child environment with the selected disposable provider.
        environment = service_environment(runtime_root, port, provider)
        # Start protected process ownership so every failure closes the one listener.
        try:
            # Start the exact production Gunicorn command from this source checkout.
            process = production_service_smoke.start_service(ROOT, environment, base_url)
            # Authenticate the synthetic bootstrap Admin once for setup-only account creation.
            admin_bootstrap = production_service_smoke.bootstrap_csrf(base_url)
            # Create the setup-only Admin session through the public production route.
            admin_login = production_service_smoke.api_request(base_url, "/api/v2/auth/login", "POST", {"email": request_latency_benchmark.SYNTHETIC_EMAIL, "password": request_latency_benchmark.SYNTHETIC_PASSWORD}, csrf=admin_bootstrap)
            # Keep Admin authority only in process memory.
            admin_session = admin_login.get("data", {}).get("session", {}) if admin_login.get("ok") is True else {}
            # Refuse setup when either independent proof is absent.
            if not admin_session.get("token") or not admin_session.get("csrf_token"):
                # Fail with one secret-free setup category.
                raise GunicornLoadSmokeError("setup Admin authentication failed")
            # Provision every independent reserved-domain account before load timing starts.
            plan = [create_user(base_url, admin_session["token"], admin_session["csrf_token"], index) for index in range(users)]
            # Start aggregate elapsed measurement before either reviewed authentication schedule.
            started = time.perf_counter()
            # Authenticate formal users serially and routine users through the reviewed eight-worker login ceiling.
            sessions = [authenticate_user(base_url, user) for user in plan] if users == FORMAL_USERS else authenticate_population(base_url, plan)
            # Refuse partial authentication before any worker can strand peers at the round barrier.
            if len(sessions) != users:
                # Keep the failure category independent from account identity or response content.
                raise GunicornLoadSmokeError("load smoke did not authenticate every session")
            # Create an exact synchronized game-action boundary only after all sessions exist.
            barrier = threading.Barrier(users)
            # Use one client worker per independent session while Gunicorn enforces its own thread limit.
            with concurrent.futures.ThreadPoolExecutor(max_workers=users) as executor:
                # Submit one round for every pre-authenticated session through the fixed population boundary.
                futures = [executor.submit(run_authenticated_round, base_url, session, index, barrier) for index, session in enumerate(sessions)]
                # Materialize every completion so worker failures remain fatal.
                completed = sum(1 for future in futures if future.result())
            # Capture one aggregate elapsed duration after all game responses returned.
            elapsed = round(time.perf_counter() - started, 3)
            # Read final pool telemetry through the protected Admin Operations API.
            operations = production_service_smoke.api_request(base_url, "/api/v2/admin/operations", token=admin_session["token"])
            # Validate and copy the provider-specific terminal pool shape.
            pool = validate_pool_telemetry(provider, operations)
        # Always close the exact process and prove its listener disappeared.
        finally:
            # Stop only when child construction reached a process object.
            if process is not None:
                # Reuse the bounded Gunicorn process-group and listener cleanup gate.
                production_service_smoke.stop_service(process, port)
    # Require complete population accounting after disposable runtime deletion.
    if completed != users:
        # Reject partial success with one fixed aggregate diagnostic.
        raise GunicornLoadSmokeError("load smoke did not complete every session")
    # Build one identifier-free exact-source acceptance report.
    report = {
        "schema": 1,
        "status": "PASS",
        "source_commit": source_commit,
        "provider": provider,
        "users": users,
        "authenticated_sessions": len(sessions),
        "completed_rounds": completed,
        "errors": 0,
        "elapsed_seconds": elapsed,
        "throughput_per_second": round(completed / elapsed, 3) if elapsed > 0 else 0,
        "gunicorn": {"workers": 1, "threads": 32},
        "pool": pool,
        "listener_closed": True,
        "requirements": ["MYSQL-011", "CORE-035", "TEST-251"],
    }
    # Publish the sanitized report only after listener and temporary-root cleanup.
    write_report(output, report)
    # Return a copy for focused hosted callers.
    return dict(report)


# Execute the explicit command-line profile with a Windows-local deferral only.
def main() -> int:
    # Parse and validate caller inputs before platform routing.
    arguments = parse_args()
    # Defer the actual Gunicorn listener to Linux CI because Gunicorn is POSIX-only.
    if os.name == "nt":
        # Validate all non-network boundaries even on unsupported local platforms.
        validate_boundaries(arguments.provider, arguments.users, arguments.report)
        # Report one stable platform classification without claiming load evidence.
        print("Gunicorn load smoke is deferred to Linux CI; boundary and unit gates remain active locally.")
        # Return success so Windows repository validation remains portable.
        return 0
    # Run the complete Linux production-stack qualification.
    run(arguments.provider, arguments.users, arguments.report)
    # Print only the aggregate provider and population dimensions.
    print(f"Gunicorn load smoke passed: provider={arguments.provider} users={arguments.users} sessions={arguments.users} rounds={arguments.users}.")
    # Return success after report publication.
    return 0


# Run the explicit CLI only when invoked as a module or script.
if __name__ == "__main__":
    # Exit through the stable command return code.
    raise SystemExit(main())
