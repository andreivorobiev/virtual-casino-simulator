# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""State-driven readiness helpers for governed Browser acceptance."""

# Import JSON encoding for one bounded shared-application failure bundle.
import json
# Import atomic filesystem primitives for one complete first-failure artifact.
import os
# Import portable paths for best-effort first-failure evidence writes.
from pathlib import Path
# Import repository identity without exposing command failures in evidence.
import subprocess
# Import exclusive unique temporary-file creation beside the final artifact.
import tempfile
# Import monotonic time so bounded readiness never depends on wall-clock changes.
import time
# Import bounded traceback extraction without retaining exception messages.
import traceback
# Import URL parsing so request outcomes retain only allowlisted same-origin paths.
from urllib.parse import urlsplit

# Import regular expressions so response predicates accept only governed report identities.
import re


# Name only terminal states that may cross from an untrusted Browser document into evidence.
SHARED_APP_STATUSES = frozenset(("pending", "ready", "error", "unavailable"))
# Name only lifecycle milestones that reveal no event payload, exception message, or route input.
SHARED_APP_MILESTONES = frozenset(("listener_installed", "dom_content_loaded", "load", "shared_app_ready", "shared_app_error", "diagnostic_unavailable"))
# Bound repeated browser-owned inventories before JSON encoding.
SHARED_APP_DIAGNOSTIC_ITEM_LIMIT = 8
# Bound every reported browser-owned count independently of hostile page data.
SHARED_APP_DIAGNOSTIC_COUNT_LIMIT = 32
# Bound the complete encoded evidence artifact to a small fixed byte budget.
SHARED_APP_DIAGNOSTIC_BYTE_LIMIT = 16_384
# Resolve repository-owned traceback paths and source identity from one fixed root.
SHARED_APP_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
# Bound source branch text while permitting only ordinary Git reference characters.
SHARED_APP_BRANCH_PATTERN = re.compile(r"[A-Za-z0-9._/-]{1,96}")
# Accept only exact lowercase Git object identities.
SHARED_APP_OBJECT_PATTERN = re.compile(r"[0-9a-f]{40}")
# Retain only fixed route-restored failure phases.
SHARED_APP_FAILURE_PHASES = frozenset(("reload", "terminal", "slots_mount"))
# Retain only fixed diagnostic capture-stage failure classes.
SHARED_APP_CAPTURE_FAILURES = frozenset(("source_identity", "browser_snapshot", "cache_capture", "service_worker_capture", "pwa_capture", "request_capture"))
# Retain only fixed same-origin request methods.
SHARED_APP_REQUEST_METHODS = frozenset(("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "OTHER"))
# Retain only fixed transport outcomes instead of raw Playwright failure text.
SHARED_APP_REQUEST_FAILURES = frozenset(("timeout", "name_resolution", "connection", "blocked", "cancelled", "other"))
# Mirror the exact externally observable production PWA display states.
SHARED_APP_PWA_STATES = frozenset(("cold-start", "warm-start", "offline", "reconnecting", "online", "route-restored", "update", "update-failed", "stale-client", "expired-session", "reconnect-failed"))
# Name exact bootstrap and Slots paths that may appear in the bounded request inventory.
SHARED_APP_REQUEST_PATHS = frozenset(("/", "/index.html", "/app.js", "/core/api.js", "/core/app_bootstrap.js", "/core/app_router.js", "/core/i18n.js", "/core/pwa.js", "/core/pwa_version.js", "/api/v2/me", "/api/v2/me/settings", "/api/v2/me/wellness", "/api/v2/me/wellness/summary", "/api/v1/casino/state", "/games/slots.js", "/api/v1/games/slots/state", "/i18n/en-US/games/slots.json", "/i18n/ru-RU/games/slots.json"))


# Distinguish a bounded reload failure from terminal-signal failure without retaining transport detail.
class SharedAppReloadError(AssertionError):
    # Keep the class intentionally behavior-free so bare route rethrow preserves its identity.
    pass


# Distinguish a bounded terminal failure from reload and module-mount failures.
class SharedAppTerminalError(AssertionError):
    # Keep the class intentionally behavior-free so bare route rethrow preserves its identity.
    pass


# Clamp one monotonic duration to the fixed Browser diagnostic range.
def _bounded_elapsed_ms(started, finished) -> int:
    # Reject booleans, malformed values, and reversed clocks without reflecting either input.
    if not isinstance(started, (int, float)) or isinstance(started, bool) or not isinstance(finished, (int, float)) or isinstance(finished, bool) or finished < started:
        # Map unavailable timing to zero.
        return 0
    # Convert seconds to milliseconds and cap the result at the governed one-minute ceiling.
    return max(0, min(int((finished - started) * 1000), 60_000))


# Map raw Playwright request failures immediately into one fixed transport class.
def _request_failure_class(value) -> str:
    # Normalize only for classification; raw text is never stored or returned.
    normalized = str(value or "").lower()
    # Classify the small set of actionable transport families.
    for fragment, category in (("timed", "timeout"), ("name_not_resolved", "name_resolution"), ("connection", "connection"), ("blocked", "blocked"), ("cancel", "cancelled")):
        # Return only the fixed category when its transport family is present.
        if fragment in normalized:
            # Discard the raw failure value immediately.
            return category
    # Collapse every other failure into one nonrevealing class.
    return "other"


# Convert one response or request failure into a bounded allowlisted outcome at capture time.
def _capture_shared_app_request(page, event, *, failed: bool) -> None:
    try:
        # Read the active context installed before reload.
        context = getattr(page, "_casino_shared_app_diagnostic_context", None)
        # Ignore events outside the exact active diagnostic boundary or beyond its fixed count.
        if not isinstance(context, dict) or len(context.get("requests", ())) >= SHARED_APP_DIAGNOSTIC_COUNT_LIMIT:
            # Leave unrelated or excess traffic unobserved.
            return
        # Resolve the request owner consistently for response and requestfailed events.
        request = event if failed else event.request
        # Parse both origins without retaining their raw forms.
        request_url = urlsplit(request.url)
        page_url = urlsplit(page.url)
        # Keep only same-origin HTTP(S) traffic from the currently loaded Casino document.
        if request_url.scheme not in {"http", "https"} or (request_url.scheme, request_url.netloc) != (page_url.scheme, page_url.netloc):
            # Drop cross-origin and pre-navigation traffic immediately.
            return
        # Retain only source-reviewed bootstrap and Slots paths with query and fragment removed.
        if request_url.path not in SHARED_APP_REQUEST_PATHS:
            # Drop every unreviewed endpoint or static asset.
            return
        # Normalize the method to the fixed enum.
        method = request.method if request.method in SHARED_APP_REQUEST_METHODS else "OTHER"
        # Build the common bounded outcome without headers, body, cookies, or URL query.
        outcome = {"method": method, "path": request_url.path, "relative_ms": _bounded_elapsed_ms(context.get("started_at"), time.monotonic())}
        # Record only a fixed failure category for requestfailed events.
        if failed:
            # Classify and immediately discard Playwright's raw failure text.
            outcome.update({"status": 0, "failure": _request_failure_class(request.failure), "from_service_worker": False})
        else:
            # Clamp HTTP status and retain only the service-worker ownership boolean.
            outcome.update({"status": event.status if isinstance(event.status, int) and 100 <= event.status <= 599 else 0, "failure": None, "from_service_worker": event.from_service_worker is True})
        # Append the already-sanitized fixed-schema outcome.
        context["requests"].append(outcome)
    except Exception:
        # Retain only one fixed capture-stage class when request inspection fails.
        context = getattr(page, "_casino_shared_app_diagnostic_context", None)
        # Update only the bounded active context.
        if isinstance(context, dict):
            # Add the fixed class idempotently without raw exception detail.
            context.setdefault("capture_failures", set()).add("request_capture")


# Install one listener before the next document can execute the shared application bootstrap. (TEST-053)
def install_shared_app_readiness_probe(page) -> None:
    # Register a fresh per-document marker before application scripts can dispatch either terminal event.
    page.add_init_script("""(() => { if(window.__casinoSharedAppReadinessProbe)return; const started=performance.now(); const marker={status:'pending',milestone:'listener_installed',milestones:[{name:'listener_installed',relativeMs:0}]}; const add=name=>{if(marker.milestones.length<8)marker.milestones.push({name,relativeMs:Math.max(0,Math.min(60000,Math.trunc(performance.now()-started)))});}; Object.defineProperty(window,'__casinoSharedAppReadinessProbe',{value:marker,configurable:false,enumerable:false,writable:false}); window.addEventListener('DOMContentLoaded',()=>add('dom_content_loaded'),{once:true}); window.addEventListener('load',()=>add('load'),{once:true}); window.addEventListener('casino:shared-app-ready',()=>{if(marker.status==='pending'){marker.status='ready';marker.milestone='shared_app_ready';add('shared_app_ready');}},{once:true}); window.addEventListener('casino:shared-app-error',()=>{if(marker.status==='pending'){marker.status='error';marker.milestone='shared_app_error';add('shared_app_error');}},{once:true}); })();""")
    # Reset one Python-owned bounded capture context for this exact route-restored attempt.
    setattr(page, "_casino_shared_app_diagnostic_context", {"started_at": time.monotonic(), "requests": [], "capture_failures": set()})
    # Install request listeners at most once because they read the newest per-attempt context dynamically.
    if callable(getattr(page, "on", None)) and not getattr(page, "_casino_shared_app_request_listeners_installed", False):
        # Observe successful responses while sanitizing them before storage.
        page.on("response", lambda response: _capture_shared_app_request(page, response, failed=False))
        # Observe failed requests while retaining only one fixed transport class.
        page.on("requestfailed", lambda request: _capture_shared_app_request(page, request, failed=True))
        # Prevent duplicate listeners across the matrix's repeated route-restored cells.
        setattr(page, "_casino_shared_app_request_listeners_installed", True)


# Wait for one allowlisted shared-application terminal marker within the existing Browser budget. (TEST-053)
def wait_for_shared_app_readiness(page, *, timeout_ms: int) -> dict:
    # Reject malformed or unbounded caller budgets before invoking Playwright.
    if not isinstance(timeout_ms, int) or isinstance(timeout_ms, bool) or timeout_ms <= 0 or timeout_ms > 60_000:
        # Keep the failure value-free so hostile inputs never enter evidence.
        raise AssertionError("shared application readiness budget was invalid")
    try:
        # Wait only until the pre-document marker reports ready or error without extending WAIT_MS.
        page.wait_for_function("() => ['ready','error'].includes(window.__casinoSharedAppReadinessProbe?.status)", timeout=timeout_ms)
    except Exception as error:
        # Convert Playwright transport detail into one stable fail-closed readiness boundary.
        raise SharedAppTerminalError("shared application readiness signal did not arrive within WAIT_MS") from error
    # Read only the allowlisted status and milestone; event detail is never retained.
    marker = page.evaluate("() => ({status:window.__casinoSharedAppReadinessProbe?.status||'unavailable',milestone:window.__casinoSharedAppReadinessProbe?.milestone||'diagnostic_unavailable'})")
    # Reject malformed or non-allowlisted terminal state before trusting the route.
    if not isinstance(marker, dict) or marker.get("status") not in SHARED_APP_STATUSES or marker.get("milestone") not in SHARED_APP_MILESTONES:
        # Avoid reflecting arbitrary Browser-owned values in the failure.
        raise SharedAppTerminalError("shared application readiness marker was malformed")
    # Fail closed when production reported its governed bootstrap error event.
    if marker["status"] != "ready" or marker["milestone"] != "shared_app_ready":
        # Preserve only the fixed allowlisted terminal class.
        raise SharedAppTerminalError("shared application reported its terminal error signal")
    # Return the bounded marker for focused acceptance evidence.
    return marker


# Reload and observe shared-application readiness under one unchanged total Browser budget. (TEST-053)
def reload_and_wait_for_shared_app_readiness(page, *, timeout_ms: int, clock=time.monotonic) -> dict:
    # Reject malformed caller budgets before establishing the one route-to-terminal deadline.
    if not isinstance(timeout_ms, int) or isinstance(timeout_ms, bool) or timeout_ms <= 0 or timeout_ms > 60_000:
        # Reuse the fixed value-free timing diagnostic.
        raise AssertionError("shared application readiness budget was invalid")
    # Start the deadline before navigation so reload and terminal observation cannot each consume WAIT_MS.
    deadline = clock() + (timeout_ms / 1000)
    # Retain the monotonic reload boundary for bounded failure evidence.
    context = getattr(page, "_casino_shared_app_diagnostic_context", None)
    # Update only the exact active diagnostic context.
    if isinstance(context, dict):
        # Record the route reload start without exposing wall-clock time.
        context["reload_started_at"] = time.monotonic()
    try:
        # Compute the remaining original budget immediately before navigation.
        reload_timeout_ms = int((deadline - clock()) * 1000)
        # Fail closed rather than starting navigation after the deadline has elapsed.
        if reload_timeout_ms <= 0:
            # Raise the same fixed reload class used for Playwright transport failure.
            raise SharedAppReloadError("shared application reload did not complete within WAIT_MS")
        # Apply only the remaining unchanged budget while retaining the exact network-idle boundary.
        page.reload(wait_until="networkidle", timeout=reload_timeout_ms)
    except Exception as error:
        # Convert navigation transport detail into one fixed fail-closed boundary.
        if isinstance(error, SharedAppReloadError):
            # Preserve the fixed helper-owned error without another wrapper.
            raise
        # Hide all Playwright transport detail behind one fixed class and message.
        raise SharedAppReloadError("shared application reload did not complete within WAIT_MS") from error
    finally:
        # Retain the monotonic navigation completion or failure boundary for diagnostics.
        if isinstance(context, dict):
            # Record only monotonic process time.
            context["reload_finished_at"] = time.monotonic()
    # Convert only the remaining fraction of the original deadline back to whole milliseconds.
    remaining_ms = int((deadline - clock()) * 1000)
    # Fail closed when navigation exhausted the shared total deadline.
    if remaining_ms <= 0:
        # Do not start a fresh terminal wait after the route budget has elapsed.
        raise SharedAppTerminalError("shared application readiness signal did not arrive within WAIT_MS")
    # Observe the terminal marker using only the remainder of the unchanged original budget.
    try:
        # Preserve the fixed terminal semantics under the one shared remainder.
        return wait_for_shared_app_readiness(page, timeout_ms=remaining_ms)
    finally:
        # Retain the terminal completion or failure boundary without changing the raised exception.
        if isinstance(context, dict):
            # Record only monotonic process time.
            context["terminal_finished_at"] = time.monotonic()


# Clamp a browser-owned diagnostic count to one nonnegative bounded integer.
def _bounded_diagnostic_count(value) -> int:
    # Reject booleans and non-integers instead of relying on Python's permissive integer coercion.
    if not isinstance(value, int) or isinstance(value, bool):
        # Map malformed values to the least revealing count.
        return 0
    # Clamp both negative and hostile large counts to the governed range.
    return max(0, min(value, SHARED_APP_DIAGNOSTIC_COUNT_LIMIT))


# Retain only a bounded sequence of explicit allowlisted string classes.
def _bounded_allowlisted_values(value, allowed: frozenset[str]) -> list[str]:
    # Treat every non-list value as unavailable diagnostic input.
    if not isinstance(value, list):
        # Return a stable empty inventory without reflecting the malformed input.
        return []
    # Drop arbitrary values and retain at most the fixed diagnostic item limit.
    return [item for item in value if isinstance(item, str) and item in allowed][:SHARED_APP_DIAGNOSTIC_ITEM_LIMIT]


# Read exact Git identity while reducing every failure to one fixed capture-stage enum.
def _shared_app_source_identity() -> tuple[dict, list[str]]:
    # Retain fixed capture failures separately from the required identity fields.
    failures = []
    try:
        # Read the exact checked-out commit and tree without invoking a shell.
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=SHARED_APP_REPOSITORY_ROOT, text=True, capture_output=True, check=True, timeout=3).stdout.strip()
        # Read the immutable tree identity independently of the commit object.
        tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=SHARED_APP_REPOSITORY_ROOT, text=True, capture_output=True, check=True, timeout=3).stdout.strip()
        # Read a local branch name when present while treating detached checkout as one fixed class.
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=SHARED_APP_REPOSITORY_ROOT, text=True, capture_output=True, check=True, timeout=3).stdout.strip() or "detached"
    except Exception:
        # Use invalid sentinel identities so publication fails closed.
        head, tree, branch = "", "", "detached"
        # Retain only the fixed capture-stage class.
        failures.append("source_identity")
    # Validate both object ids and sanitize the branch before any evidence encoding.
    valid_head = head if SHARED_APP_OBJECT_PATTERN.fullmatch(head) else ""
    # Validate the tree independently so a commit id cannot be substituted.
    valid_tree = tree if SHARED_APP_OBJECT_PATTERN.fullmatch(tree) else ""
    # Reject traversal-like or boundary-slash branch forms despite their allowlisted characters.
    valid_branch = branch if SHARED_APP_BRANCH_PATTERN.fullmatch(branch) and ".." not in branch and not branch.startswith("/") and not branch.endswith("/") else "detached"
    # Mark invalid object identity with the same nonrevealing capture-stage enum.
    if not valid_head or not valid_tree:
        # Add idempotently so schema size remains bounded.
        failures = list(dict.fromkeys((*failures, "source_identity")))
    # Return only fixed source fields and bounded capture classes.
    return {"head": valid_head, "tree": valid_tree, "branch": valid_branch}, failures


# Convert one exception into fixed class and project-relative frame evidence.
def _sanitize_shared_app_failure(failure, phase: str) -> dict:
    # Map helper-owned failures before the caller-supplied phase fallback.
    fixed_phase = "reload" if isinstance(failure, SharedAppReloadError) else "terminal" if isinstance(failure, SharedAppTerminalError) else phase if phase in SHARED_APP_FAILURE_PHASES else "slots_mount"
    # Map concrete Python/Playwright classes into a fixed non-message enum.
    exception_name = type(failure).__name__ if failure is not None else ""
    # Preserve only reviewed actionable class families.
    exception_class = {"SharedAppReloadError": "shared_reload", "SharedAppTerminalError": "shared_terminal", "TimeoutError": "playwright_timeout", "AssertionError": "assertion", "RuntimeError": "runtime"}.get(exception_name, "generic")
    # Build at most eight repo-owned frames from the original traceback.
    frames = []
    # Extract structured frames without formatting source lines or exception messages.
    for frame in traceback.extract_tb(failure.__traceback__) if failure is not None and failure.__traceback__ is not None else ():
        try:
            # Resolve and relativize only paths owned by this exact checkout.
            relative = Path(frame.filename).resolve().relative_to(SHARED_APP_REPOSITORY_ROOT).as_posix()
        except (OSError, ValueError):
            # Drop interpreter, dependency, and out-of-repository frames.
            continue
        # Classify the frame owner without retaining arbitrary source text.
        function_class = "readiness_helper" if relative == "tests/browser_readiness.py" else "slots_case" if relative == "tests/cases/browser/roulette_slots_keno.py" else "project"
        # Retain a bounded identifier-like function name or one fixed fallback.
        function_name = frame.name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", frame.name or "") else "unknown"
        # Retain only positive bounded line positions.
        frames.append({"path": relative[:180], "line": max(1, min(int(frame.lineno), 1_000_000)), "function_class": function_class, "function": function_name})
    # Keep only the nearest eight repo-owned frames.
    return {"phase": fixed_phase, "exception_class": exception_class, "frames": frames[-SHARED_APP_DIAGNOSTIC_ITEM_LIMIT:]}


# Convert a potentially hostile Browser snapshot into the fixed evidence schema.
def sanitize_shared_app_failure_snapshot(snapshot, *, source=None, failure=None, phase="terminal", context=None) -> dict:
    # Read only dictionaries while ignoring arbitrary top-level Browser-owned fields.
    browser = snapshot if isinstance(snapshot, dict) else {}
    # Read each governed section independently so one malformed layer cannot leak another.
    readiness = browser.get("readiness") if isinstance(browser.get("readiness"), dict) else {}
    document = browser.get("document") if isinstance(browser.get("document"), dict) else {}
    caches = browser.get("caches") if isinstance(browser.get("caches"), dict) else {}
    service_workers = browser.get("serviceWorkers") if isinstance(browser.get("serviceWorkers"), dict) else {}
    pwa = browser.get("pwa") if isinstance(browser.get("pwa"), dict) else {}
    # Normalize the Python-owned capture context independently of Browser data.
    capture = context if isinstance(context, dict) else {}
    # Allow only browser-standard document readiness states.
    ready_state = document.get("readyState") if document.get("readyState") in {"loading", "interactive", "complete"} else "unknown"
    # Retain only fixed cache-name classifications, never raw CacheStorage keys.
    cache_classes = _bounded_allowlisted_values(caches.get("classes"), frozenset(("casino_shell", "other")))
    # Read a bounded list of already-classified service-worker entries.
    raw_registrations = service_workers.get("registrations") if isinstance(service_workers.get("registrations"), list) else []
    # Build a fresh sanitized registration list without any raw scope or script URL values.
    registrations = []
    # Inspect at most the fixed prefix even when a hostile page returns an unbounded array.
    for raw in raw_registrations[:SHARED_APP_DIAGNOSTIC_ITEM_LIMIT]:
        # Ignore non-dictionary registration rows completely.
        if not isinstance(raw, dict):
            # Continue without preserving the hostile value.
            continue
        # Allow only fixed classifications and browser-standard worker states.
        registrations.append({"scope_class": raw.get("scopeClass") if raw.get("scopeClass") in {"same_origin", "other"} else "other", "script_class": raw.get("scriptClass") if raw.get("scriptClass") in {"casino_sw", "other"} else "other", "state": raw.get("state") if raw.get("state") in {"installing", "installed", "activating", "activated", "redundant", "missing"} else "unknown"})
    # Sanitize the controller independently from registration inventory.
    raw_controller = service_workers.get("controller") if isinstance(service_workers.get("controller"), dict) else {}
    # Retain only fixed controller facts.
    controller = {"present": raw_controller.get("present") is True, "script_class": raw_controller.get("scriptClass") if raw_controller.get("scriptClass") in {"casino_sw", "other", "missing"} else "other", "state": raw_controller.get("state") if raw_controller.get("state") in {"installing", "installed", "activating", "activated", "redundant", "missing"} else "unknown"}
    # Sanitize up to eight fixed bootstrap milestones and clamped relative times.
    milestones = []
    # Inspect only a bounded Browser-provided prefix.
    for raw in readiness.get("milestones", [])[:SHARED_APP_DIAGNOSTIC_ITEM_LIMIT] if isinstance(readiness.get("milestones"), list) else ():
        # Retain only structured allowlisted milestones.
        if isinstance(raw, dict) and raw.get("name") in SHARED_APP_MILESTONES:
            # Clamp Browser timing independently of its raw number type.
            relative_ms = raw.get("relativeMs") if isinstance(raw.get("relativeMs"), int) and not isinstance(raw.get("relativeMs"), bool) else 0
            # Append only fixed names and bounded integer time.
            milestones.append({"name": raw["name"], "relative_ms": max(0, min(relative_ms, 60_000))})
    # Revalidate every Python-captured request outcome before publication.
    requests = []
    # Inspect at most the fixed request budget.
    for raw in capture.get("requests", [])[:SHARED_APP_DIAGNOSTIC_COUNT_LIMIT] if isinstance(capture.get("requests"), list) else ():
        # Drop malformed or unallowlisted rows completely.
        if not isinstance(raw, dict) or raw.get("method") not in SHARED_APP_REQUEST_METHODS or raw.get("path") not in SHARED_APP_REQUEST_PATHS:
            # Continue without reflecting hostile request values.
            continue
        # Retain only valid status, fixed failure, boolean ownership, and clamped relative time.
        requests.append({"method": raw["method"], "path": raw["path"], "status": raw.get("status") if isinstance(raw.get("status"), int) and not isinstance(raw.get("status"), bool) and 0 <= raw.get("status") <= 599 else 0, "failure": raw.get("failure") if raw.get("failure") in SHARED_APP_REQUEST_FAILURES else None, "from_service_worker": raw.get("from_service_worker") is True, "relative_ms": max(0, min(raw.get("relative_ms"), 60_000)) if isinstance(raw.get("relative_ms"), int) and not isinstance(raw.get("relative_ms"), bool) else 0})
    # Merge Browser and Python capture failures through the fixed bounded enum.
    capture_failures = _bounded_allowlisted_values(list(browser.get("captureFailures", [])) + list(capture.get("capture_failures", [])), SHARED_APP_CAPTURE_FAILURES)
    # Compute monotonic phase timings without wall-clock fields.
    reload_ms = _bounded_elapsed_ms(capture.get("reload_started_at"), capture.get("reload_finished_at"))
    # Compute terminal time only after reload completes.
    terminal_ms = _bounded_elapsed_ms(capture.get("reload_finished_at"), capture.get("terminal_finished_at"))
    # Compute total time from reload start through capture.
    total_ms = _bounded_elapsed_ms(capture.get("reload_started_at"), capture.get("captured_at"))
    # Return one fixed schema containing no raw event, URL query, scope, cache key, or exception message.
    return {"schema": "casino-shared-app-first-failure-v2", "case_id": "BR-SLOT-ECONOMICS-001", "boundary": "route_restored_reload", "source": source if isinstance(source, dict) else {"head": "", "tree": "", "branch": "detached"}, "failure": _sanitize_shared_app_failure(failure, phase), "timing": {"reload_ms": reload_ms, "terminal_ms": terminal_ms, "total_ms": total_ms}, "bootstrap": {"status": readiness.get("status") if readiness.get("status") in SHARED_APP_STATUSES else "unavailable", "milestone": readiness.get("milestone") if readiness.get("milestone") in SHARED_APP_MILESTONES else "diagnostic_unavailable", "milestones": milestones}, "document": {"ready_state": ready_state, "shell_present": document.get("shellPresent") is True, "wallet_present": document.get("walletPresent") is True, "route_present": document.get("routePresent") is True, "slots_root_count": _bounded_diagnostic_count(document.get("slotsRootCount"))}, "requests": requests, "pwa": {"present": pwa.get("present") is True, "state": pwa.get("state") if pwa.get("state") in SHARED_APP_PWA_STATES else "unknown"}, "caches": {"count": _bounded_diagnostic_count(caches.get("count")), "truncated": caches.get("truncated") is True or len(cache_classes) >= SHARED_APP_DIAGNOSTIC_ITEM_LIMIT, "key_classes": cache_classes}, "service_workers": {"count": _bounded_diagnostic_count(service_workers.get("count")), "truncated": service_workers.get("truncated") is True or len(raw_registrations) > SHARED_APP_DIAGNOSTIC_ITEM_LIMIT, "controller": controller, "registrations": registrations}, "capture_failures": capture_failures}


# Validate one existing artifact completely before allowing first-valid-wins preservation.
def _valid_shared_app_artifact(payload, source: dict) -> bool:
    try:
        # Require the exact fixed schema, case, boundary, and current source identity.
        if not isinstance(payload, dict) or payload.get("schema") != "casino-shared-app-first-failure-v2" or payload.get("case_id") != "BR-SLOT-ECONOMICS-001" or payload.get("boundary") != "route_restored_reload" or payload.get("source") != source:
            # Reject stale, partial, or cross-case evidence.
            return False
        # Require valid immutable source ids and sanitized branch text.
        if not SHARED_APP_OBJECT_PATTERN.fullmatch(source.get("head", "")) or not SHARED_APP_OBJECT_PATTERN.fullmatch(source.get("tree", "")) or not SHARED_APP_BRANCH_PATTERN.fullmatch(source.get("branch", "")):
            # Reject incomplete source identity.
            return False
        # Require a fixed failure phase/class and no more than eight bounded repo-relative frames.
        failure = payload.get("failure", {})
        # Validate the complete fixed failure shape.
        if failure.get("phase") not in SHARED_APP_FAILURE_PHASES or failure.get("exception_class") not in {"shared_reload", "shared_terminal", "playwright_timeout", "assertion", "runtime", "generic"} or not isinstance(failure.get("frames"), list) or len(failure["frames"]) > SHARED_APP_DIAGNOSTIC_ITEM_LIMIT:
            # Reject malformed failure evidence.
            return False
        # Require every frame to remain project-relative and bounded.
        if any(not isinstance(frame, dict) or set(frame) != {"path", "line", "function_class", "function"} or not isinstance(frame.get("path"), str) or frame["path"].startswith("/") or ".." in Path(frame["path"]).parts or not isinstance(frame.get("line"), int) or isinstance(frame.get("line"), bool) or not 0 < frame["line"] <= 1_000_000 or frame.get("function_class") not in {"readiness_helper", "slots_case", "project"} or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}|unknown", frame.get("function", "")) for frame in failure["frames"]):
            # Reject unsafe or incomplete frame rows.
            return False
        # Require every timing to be a bounded nonnegative integer.
        if any(not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 60_000 for value in payload.get("timing", {}).values()) or set(payload.get("timing", {})) != {"reload_ms", "terminal_ms", "total_ms"}:
            # Reject malformed monotonic timings.
            return False
        # Require bounded request, milestone, registration, cache, and capture inventories.
        if len(payload.get("requests", ())) > SHARED_APP_DIAGNOSTIC_COUNT_LIMIT or len(payload.get("bootstrap", {}).get("milestones", ())) > SHARED_APP_DIAGNOSTIC_ITEM_LIMIT or len(payload.get("service_workers", {}).get("registrations", ())) > SHARED_APP_DIAGNOSTIC_ITEM_LIMIT or len(payload.get("caches", {}).get("key_classes", ())) > SHARED_APP_DIAGNOSTIC_ITEM_LIMIT or any(item not in SHARED_APP_CAPTURE_FAILURES for item in payload.get("capture_failures", ())):
            # Reject any unbounded or unallowlisted repeated field.
            return False
        # Require every request to remain source-allowlisted and fixed-schema.
        if any(not isinstance(row, dict) or set(row) != {"method", "path", "status", "failure", "from_service_worker", "relative_ms"} or row.get("method") not in SHARED_APP_REQUEST_METHODS or row.get("path") not in SHARED_APP_REQUEST_PATHS or not isinstance(row.get("status"), int) or isinstance(row.get("status"), bool) or not 0 <= row["status"] <= 599 or row.get("failure") not in SHARED_APP_REQUEST_FAILURES | {None} or not isinstance(row.get("from_service_worker"), bool) or not isinstance(row.get("relative_ms"), int) or isinstance(row.get("relative_ms"), bool) or not 0 <= row["relative_ms"] <= 60_000 for row in payload.get("requests", ())):
            # Reject arbitrary request data.
            return False
        # Require the complete fixed bootstrap and milestone schema.
        bootstrap = payload.get("bootstrap", {})
        # Reject absent or arbitrary terminal state.
        if set(bootstrap) != {"status", "milestone", "milestones"} or bootstrap.get("status") not in SHARED_APP_STATUSES or bootstrap.get("milestone") not in SHARED_APP_MILESTONES or any(not isinstance(row, dict) or set(row) != {"name", "relative_ms"} or row.get("name") not in SHARED_APP_MILESTONES or not isinstance(row.get("relative_ms"), int) or isinstance(row.get("relative_ms"), bool) or not 0 <= row["relative_ms"] <= 60_000 for row in bootstrap.get("milestones", ())):
            # Reject partial or unbounded lifecycle evidence.
            return False
        # Require the exact document fact shape and bounded Slots root count.
        document = payload.get("document", {})
        # Validate all booleans and the browser-standard readiness enum.
        if set(document) != {"ready_state", "shell_present", "wallet_present", "route_present", "slots_root_count"} or document.get("ready_state") not in {"loading", "interactive", "complete", "unknown"} or any(not isinstance(document.get(name), bool) for name in ("shell_present", "wallet_present", "route_present")) or not isinstance(document.get("slots_root_count"), int) or isinstance(document.get("slots_root_count"), bool) or not 0 <= document["slots_root_count"] <= SHARED_APP_DIAGNOSTIC_COUNT_LIMIT:
            # Reject incomplete DOM and surface facts.
            return False
        # Require the exact PWA presence and fixed state class.
        pwa = payload.get("pwa", {})
        # Reject arbitrary PWA strings or nonboolean presence.
        if set(pwa) != {"present", "state"} or not isinstance(pwa.get("present"), bool) or pwa.get("state") not in SHARED_APP_PWA_STATES | {"unknown"}:
            # Reject malformed PWA evidence.
            return False
        # Require bounded CacheStorage counts and fixed production-key classes only.
        caches = payload.get("caches", {})
        # Reject raw or malformed cache inventory fields.
        if set(caches) != {"count", "truncated", "key_classes"} or not isinstance(caches.get("count"), int) or isinstance(caches.get("count"), bool) or not 0 <= caches["count"] <= SHARED_APP_DIAGNOSTIC_COUNT_LIMIT or not isinstance(caches.get("truncated"), bool) or any(value not in {"casino_shell", "other"} for value in caches.get("key_classes", ())):
            # Reject unsafe cache evidence.
            return False
        # Require the fixed service-worker inventory and controller shape.
        workers = payload.get("service_workers", {})
        # Reject raw scope, script, or malformed count data.
        if set(workers) != {"count", "truncated", "controller", "registrations"} or not isinstance(workers.get("count"), int) or isinstance(workers.get("count"), bool) or not 0 <= workers["count"] <= SHARED_APP_DIAGNOSTIC_COUNT_LIMIT or not isinstance(workers.get("truncated"), bool):
            # Reject malformed service-worker summary.
            return False
        # Validate controller and registration rows through fixed classes only.
        controller = workers.get("controller", {})
        # Reject raw controller data or unreviewed states.
        if set(controller) != {"present", "script_class", "state"} or not isinstance(controller.get("present"), bool) or controller.get("script_class") not in {"casino_sw", "other", "missing"} or controller.get("state") not in {"installing", "installed", "activating", "activated", "redundant", "missing", "unknown"} or any(not isinstance(row, dict) or set(row) != {"scope_class", "script_class", "state"} or row.get("scope_class") not in {"same_origin", "other"} or row.get("script_class") not in {"casino_sw", "other"} or row.get("state") not in {"installing", "installed", "activating", "activated", "redundant", "missing", "unknown"} for row in workers.get("registrations", ())):
            # Reject malformed or raw worker inventory.
            return False
        # Require all fixed top-level sections so partial JSON cannot poison later capture.
        return set(payload) == {"schema", "case_id", "boundary", "source", "failure", "timing", "bootstrap", "document", "requests", "pwa", "caches", "service_workers", "capture_failures"}
    except Exception:
        # Treat every parser or type failure as invalid existing evidence.
        return False


# Persist one bounded sanitized first-valid failure bundle without replacing the triggering exception. (TEST-053)
def persist_shared_app_first_failure(page, target, *, failure=None, phase="slots_mount", encoder=json.dumps, writer=None, fsyncer=os.fsync, replacer=os.replace) -> bool:
    # Retain the unique temporary path for best-effort cleanup across every failure stage.
    temporary_path = None
    # Retain an exclusive descriptor until it is safely closed.
    descriptor = None
    try:
        # Normalize the caller-owned artifact path without including it in the evidence payload.
        evidence_path = Path(target)
        # Resolve and validate exact source identity before considering existing evidence.
        source, source_failures = _shared_app_source_identity()
        # Fail closed when exact head and tree identities are unavailable.
        if not source["head"] or not source["tree"]:
            # Avoid publishing evidence that cannot bind to one immutable checkout.
            return False
        # Preserve only an existing complete current-source artifact within the fixed byte bound.
        if evidence_path.exists():
            try:
                # Read no more than one byte beyond the fixed artifact ceiling.
                existing_bytes = evidence_path.read_bytes()[:SHARED_APP_DIAGNOSTIC_BYTE_LIMIT + 1]
                # Preserve the first valid complete artifact for this exact source.
                if len(existing_bytes) <= SHARED_APP_DIAGNOSTIC_BYTE_LIMIT and _valid_shared_app_artifact(json.loads(existing_bytes.decode("utf-8")), source):
                    # Report that the current valid first artifact won.
                    return False
            except Exception:
                # Treat malformed, partial, unreadable, or oversized targets as replaceable poison.
                pass
        # Read the active bounded Python capture context and stamp capture time monotonically.
        context = getattr(page, "_casino_shared_app_diagnostic_context", None)
        # Create a minimal bounded context for tests or very-early failures.
        if not isinstance(context, dict):
            # Avoid relying on page-owned arbitrary attributes.
            context = {"requests": [], "capture_failures": set()}
        # Retain only the monotonic capture boundary.
        context["captured_at"] = time.monotonic()
        # Carry source-capture failures into the fixed bounded enum.
        context.setdefault("capture_failures", set()).update(source_failures)
        try:
            # Collect only pre-classified bounded values; raw cache names and registration URLs never leave the document.
            snapshot = page.evaluate("""async () => { const failures=[]; const marker=window.__casinoSharedAppReadinessProbe||{}; const bounded=async(factory,failure)=>{try{return await Promise.race([factory(),new Promise((_,reject)=>setTimeout(reject,250))]);}catch(_){failures.push(failure);return[];}}; const [cacheNames,registrations]=await Promise.all([bounded(()=>caches.keys(),'cache_capture'),bounded(()=>navigator.serviceWorker.getRegistrations(),'service_worker_capture')]); let pwaState='unknown'; try { const raw=window.CasinoPwa?.state?.(); pwaState=['cold-start','warm-start','offline','reconnecting','online','route-restored','update','update-failed','stale-client','expired-session','reconnect-failed'].includes(raw)?raw:'unknown'; } catch (_) { failures.push('pwa_capture'); } const cacheClasses=cacheNames.slice(0,8).map(name=>String(name).startsWith('casino-static-shell-v')?'casino_shell':'other'); const classifyWorker=worker=>{ let scriptClass='missing'; try { scriptClass=worker&&new URL(worker.scriptURL,location.href).pathname.endsWith('/sw.js')?'casino_sw':worker?'other':'missing'; } catch (_) { scriptClass='other'; } return {scriptClass,state:worker?.state||'missing'}; }; const workerRows=registrations.slice(0,8).map(registration=>{ const worker=registration.installing||registration.waiting||registration.active; let scopeClass='other'; try { scopeClass=new URL(registration.scope,location.href).origin===location.origin?'same_origin':'other'; } catch (_) {} return {scopeClass,...classifyWorker(worker)}; }); const controller=classifyWorker(navigator.serviceWorker?.controller); return {captureFailures:failures,readiness:{status:marker.status||'unavailable',milestone:marker.milestone||'diagnostic_unavailable',milestones:Array.isArray(marker.milestones)?marker.milestones.slice(0,8):[]},document:{readyState:document.readyState,shellPresent:document.body?.dataset?.testid==='pwa-shell',walletPresent:Boolean(document.querySelector('[data-testid="premium-wallet"]')),routePresent:Boolean(document.querySelector('#view')),slotsRootCount:document.querySelectorAll('[data-testid="slots-premium"]').length},pwa:{present:Boolean(window.CasinoPwa),state:pwaState},caches:{count:cacheNames.length,truncated:cacheNames.length>8,classes:cacheClasses},serviceWorkers:{count:registrations.length,truncated:registrations.length>8,controller:{present:Boolean(navigator.serviceWorker?.controller),...controller},registrations:workerRows}}; }""")
        except Exception:
            # Retain one fixed browser-capture failure and continue with an empty snapshot.
            context.setdefault("capture_failures", set()).add("browser_snapshot")
            # Keep the artifact structurally complete without Browser-owned detail.
            snapshot = {}
        # Re-sanitize Browser and Python data before any encoder can observe it.
        payload = sanitize_shared_app_failure_snapshot(snapshot, source=source, failure=failure, phase=phase, context=context)
        # Encode deterministically so artifact size and review diffs stay bounded.
        encoded = encoder(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        # Reject hostile encoders and any output beyond the fixed byte budget.
        if not isinstance(encoded, str) or len(encoded.encode("utf-8")) > SHARED_APP_DIAGNOSTIC_BYTE_LIMIT:
            # Skip the artifact while preserving the original Browser exception.
            return False
        # Validate the exact final schema before touching the destination.
        if not _valid_shared_app_artifact(payload, source):
            # Reject any internal partial artifact fail closed.
            return False
        # Create only the fixed case-owned evidence directory.
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        # Create one uniquely named same-directory temporary with exclusive OS ownership.
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{evidence_path.name}.", suffix=".tmp", dir=evidence_path.parent)
        # Resolve the unique cleanup path after exclusive creation succeeds.
        temporary_path = Path(temporary_name)
        # Encode once to bounded UTF-8 bytes for atomic publication.
        encoded_bytes = encoded.encode("utf-8")
        # Use the injected focused-test writer only against the unique temporary.
        if writer is not None:
            # Close the exclusive descriptor before the injected writer owns the temp path.
            os.close(descriptor); descriptor = None
            # Delegate only bounded sanitized text without exposing Browser-owned raw values.
            writer(temporary_path, encoded)
            # Reopen the unique temporary for durable flush and fsync verification.
            with temporary_path.open("rb+") as stream:
                # Flush any user-space writer buffers before durability is requested.
                stream.flush()
                # Require the injected or real fsync stage to succeed.
                fsyncer(stream.fileno())
        else:
            # Own the exclusive descriptor through write, flush, fsync, and close.
            with os.fdopen(descriptor, "wb") as stream:
                # Transfer descriptor ownership to the context manager exactly once.
                descriptor = None
                # Write only the complete bounded encoded bytes.
                stream.write(encoded_bytes)
                # Flush Python buffers before requesting filesystem durability.
                stream.flush()
                # Require the injected or real fsync stage to succeed.
                fsyncer(stream.fileno())
        # Atomically replace a poisoned partial target or publish the first valid target.
        replacer(temporary_path, evidence_path)
        # Clear the cleanup handle only after atomic publication succeeds.
        temporary_path = None
        # Report one successful best-effort artifact write.
        return True
    except Exception:
        # Suppress diagnostics-only failures so the surrounding bare raise preserves the original exception.
        return False
    finally:
        # Close any descriptor whose ownership was not transferred after an early failure.
        if descriptor is not None:
            try:
                # Release the exclusive OS handle without masking the original diagnostic failure.
                os.close(descriptor)
            except OSError:
                # Ignore cleanup-only descriptor failures.
                pass
        # Remove any unpublished unique temporary after encode/write/fsync/replace failure.
        if temporary_path is not None:
            try:
                # Delete only the exact temp path returned by exclusive creation.
                temporary_path.unlink(missing_ok=True)
            except OSError:
                # Ignore cleanup-only filesystem failures.
                pass


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
