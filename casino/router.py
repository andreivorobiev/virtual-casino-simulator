# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Route registration, request coercion, identity guards, and response-envelope dispatch.
import inspect
import re
# Import monotonic timing for coarse guest latency buckets.
import time
from urllib.parse import urlparse, parse_qs
from casino.errors import CasinoError, NotFoundError
# Import the shared resolver so every current and future game route is session-bound centrally.
from casino.core.request_player import resolve_authenticated_player, sanitize_game_intent
# Import descriptor-owned rule coercion so every settings route shares one server boundary.
from casino.core import game_rules
# Import de-identified guest telemetry at the shared route boundary so game modules stay isolated.
from casino.core import auth, guest_analytics, ledger

# Determine whether a successful game response contains a terminal outcome marker.
def _contains_round_outcome(value, depth: int = 0) -> bool:
    # Stop recursive inspection at a small fixed depth so arbitrary response shapes stay bounded.
    if depth > 4:
        # Report no marker outside the approved inspection depth.
        return False
    # Inspect mapping keys used by settled game responses without retaining their values.
    if isinstance(value, dict):
        # Recognize an explicit terminal status on a round-shaped response.
        if value.get("round_id") and str(value.get("status") or "").lower() in ("settled", "complete", "completed", "won", "lost", "push", "folded"):
            # Report an authoritative completed-round classification.
            return True
        # Recognize common terminal markers only when the response also exposes round-like state.
        if any(value.get(key) is not None for key in ("outcome", "winner", "payout", "settlement")) and any(key in value for key in ("round_id", "round", "result", "coup")):
            # Report a completed-round classification for telemetry counters.
            return True
        # Recurse into mapping values without copying response data into telemetry.
        return any(_contains_round_outcome(child, depth + 1) for child in value.values())
    # Recurse into bounded collection elements returned by some game endpoints.
    if isinstance(value, (list, tuple)):
        # Inspect at most the first twenty elements to keep classification bounded.
        return any(_contains_round_outcome(child, depth + 1) for child in value[:20])
    # Scalar values cannot contain a structured terminal marker.
    return False

# Report whether one request belongs to a disposable guest analytics row.
def _guest_binding(context: dict) -> tuple[dict, str]:
    # Read the authenticated user published by either HTTP adapter.
    user = context.get("user") or {}
    # Continue only for a disposable principal carrying the one-way analytics id.
    if str(user.get("identity_provider") or "").lower() != "guest" or not user.get("guest_analytics_id"):
        # Return no binding for registered accounts or anonymous routes.
        return {}, ""
    # Return the authenticated user and unrelated analytics id without persisting either together.
    return user, str(user.get("guest_analytics_id"))

# Snapshot recent authoritative ledger identities before one guest game mutation.
def _ledger_snapshot(player_id: str) -> set[str]:
    # Read a bounded recent window sufficient for any one game action.
    rows = ledger.read_recent(player_id, 250)
    # Return only storage-issued ledger ids for difference calculation.
    return {str(row.get("ledger_id")) for row in rows if row.get("ledger_id")}

# Calculate fake-token wager and return aggregates from newly committed ledger rows.
def _ledger_movement(player_id: str, before: set[str]) -> tuple[float, float]:
    # Read the same bounded ledger window after the authoritative handler succeeds.
    rows = ledger.read_recent(player_id, 250)
    # Select only rows not present before the action began.
    added = [row for row in rows if row.get("ledger_id") and str(row.get("ledger_id")) not in before]
    # Sum negative signed amounts as positive wager/debit totals.
    wagered = round(sum(abs(float(row.get("amount") or 0)) for row in added if float(row.get("amount") or 0) < 0), 2)
    # Sum positive signed amounts as returned-credit totals.
    returned = round(sum(float(row.get("amount") or 0) for row in added if float(row.get("amount") or 0) > 0), 2)
    # Return only aggregate fake-token movement, never ledger ids or detail payloads.
    return wagered, returned

# Record one successful game request for a disposable guest without retaining request or response data.
def _record_guest_game_event(context: dict, method: str, path: str, result, elapsed_ms: float, ledger_before: set[str] | None = None) -> None:
    # Read the authenticated guest binding established before dispatch.
    user, analytics_id = _guest_binding(context)
    # Stop without telemetry for every non-guest request.
    if not analytics_id:
        # Preserve registered game behavior unchanged.
        return
    # Extract only the registered game slug segment from the normalized path.
    game = path.split("/")[4] if len(path.split("/")) > 4 else ""
    # Read only server-route path segments after the catalog game key.
    route_tail = path.split("/")[5:]
    # Normalize one low-cardinality action category without using request data.
    category = guest_analytics.action_category(route_tail)
    # Record only canonical state reads as game opens; config, catalog, and stats remain uncounted.
    if method.upper() == "GET":
        # Stop when a secondary read-only route is not the mounted game state.
        if not route_tail or route_tail[-1] == "state":
            # Record the server-observed game-open milestone and coarse latency.
            guest_analytics.record_event(analytics_id, "game_open", game, latency_ms=elapsed_ms)
        # Return after every read-only request without ledger inspection.
        return
    # Calculate authoritative fake-token movement committed during this action.
    wagered, returned = _ledger_movement(user.get("player_id"), ledger_before or set())
    # Classify terminal results without persisting response values.
    completed = _contains_round_outcome(result)
    # Classify route-authored round starts independently from terminal results.
    started = guest_analytics.starts_round(category)
    # Increment safe de-identified counters, categories, ledger totals, and milestones.
    guest_analytics.record_event(analytics_id, "game_action", game, action=category, latency_ms=elapsed_ms, wagered=wagered, returned=returned, round_started=started, round_completed=completed)

# Record one sanitized failed guest game request and preserve the original exception.
def _record_guest_game_error(context: dict, path: str, error_category: str, elapsed_ms: float) -> None:
    # Read the authenticated guest binding without storing auth or player identifiers.
    _, analytics_id = _guest_binding(context)
    # Stop for every registered or anonymous request.
    if not analytics_id:
        # Preserve non-guest failure behavior unchanged.
        return
    # Extract only the registered game slug and route-authored action category.
    segments = path.split("/")
    # Read the normalized catalog game key.
    game = segments[4] if len(segments) > 4 else ""
    # Normalize the action from server route segments only.
    category = guest_analytics.action_category(segments[5:])
    # Persist only the sanitized category and coarse latency bucket.
    guest_analytics.record_event(analytics_id, "game_error", game, action=category, latency_ms=elapsed_ms, error_category=error_category)

# Define the Route class that groups related behavior.
class Route:
    # Define the __init__ function used by this module.
    def __init__(self, method: str, pattern: str, handler):
        # Set self.method to the value needed for the next operation.
        self.method = method.upper()
        # Set self.pattern to the value needed for the next operation.
        self.pattern = pattern
        # Set self.handler to the value needed for the next operation.
        self.handler = handler
        # Set self.regex to the value needed for the next operation.
        self.regex = re.compile("^" + pattern + "$")

    # Define the match function used by this module.
    def match(self, method: str, path: str):
        if self.method != method.upper():
            return None
        return self.regex.match(path)

# Define the Router class that groups related behavior.
class Router:
    # Define the __init__ function used by this module.
    def __init__(self):
        # Set self.routes to the value needed for the next operation.
        self.routes = []

    # Define the add function used by this module.
    def add(self, method: str, pattern: str, handler):
        self.routes.append(Route(method, pattern, handler))
        return handler

    # Define the get function used by this module.
    def get(self, pattern: str):
        # Define the deco function used by this module.
        def deco(fn):
            self.add("GET", pattern, fn); return fn
        return deco

    # Define the post function used by this module.
    def post(self, pattern: str):
        # Define the deco function used by this module.
        def deco(fn):
            self.add("POST", pattern, fn); return fn
        return deco

    # Define patch so v2 Admin updates can use their published HTTP method.
    def patch(self, pattern: str):
        # Define the decorator that registers a PATCH route.
        def deco(fn):
            # Register the handler and return it unchanged.
            self.add("PATCH", pattern, fn); return fn
        # Return the route decorator to the caller.
        return deco

    # Define the delete function used by this module.
    def delete(self, pattern: str):
        # Define the deco function used by this module.
        def deco(fn):
            self.add("DELETE", pattern, fn); return fn
        return deco

    # Define the dispatch function used by this module.
    def dispatch(self, method: str, raw_path: str, body: dict | None = None, context: dict | None = None):
        # Normalize the mutable request body before shared resolver and route handlers use it.
        body = body or {}
        # Normalize request context so direct router tests receive the same resolver behavior.
        context = context or {}
        # Set parsed to the value needed for the next operation.
        parsed = urlparse(raw_path)
        # Set path to the value needed for the next operation.
        path = parsed.path
        # Parse blank values and preserve duplicate values so OAuth callbacks can reject ambiguity.
        parsed_query = parse_qs(parsed.query, keep_blank_values=True)
        # Keep ordinary single values scalar while passing duplicates as lists to strict handlers.
        query = {key: values[0] if len(values) == 1 else values for key, values in parsed_query.items()}
        # Apply the shared authenticated-player resolver to every game endpoint before dispatch.
        if path.startswith("/api/v1/games/"):
            # Remove client-authored outcome, privilege, wallet, and round-control fields before game dispatch.
            body = sanitize_game_intent(body)
            # Resolve the session-bound player while preserving explicit Admin/test compatibility.
            player_id = resolve_authenticated_player(context, body, query)
            # Replace stale or malicious payload player ids with the resolved identity.
            body["player_id"] = player_id
            # Replace stale or malicious query player ids with the same resolved identity.
            query["player_id"] = player_id
            # Publish the resolution for future context-aware game handlers.
            context["resolved_player_id"] = player_id
        for route in self.routes:
            # Set m to the value needed for the next operation.
            m = route.match(method, path)
            if m:
                # Set kwargs to the value needed for the next operation.
                kwargs = m.groupdict()
                # Measure one game request with a monotonic clock so wall-clock changes cannot affect buckets.
                started_at = time.perf_counter()
                # Read the authenticated guest binding once before any mutation.
                guest_user, guest_analytics_id = _guest_binding(context) if path.startswith("/api/v1/games/") else ({}, "")
                # Snapshot authoritative ledger ids only for a guest game mutation.
                ledger_before = _ledger_snapshot(guest_user.get("player_id")) if guest_analytics_id and method.upper() != "GET" else set()
                # Start protected handler execution so sanitized guest failures are counted before rethrow.
                try:
                    # Coerce descriptor-owned settings inside telemetry protection but before action consumption or handler state checks. (SEC-014)
                    if path.startswith("/api/v1/games/"):
                        # Replace only declared settings values with canonical bounded representations.
                        body = game_rules.coerce_request(path, body)
                    # Consume one disposable-session action allowance before a state-changing game route.
                    if guest_analytics_id and method.upper() != "GET":
                        # Persist the bounded attempt count without affecting registered users.
                        auth.consume_guest_action(context.get("session") or {}, guest_user)
                    # Branch when the route handler accepts the request context.
                    if "context" in inspect.signature(route.handler).parameters:
                        # Execute the context-aware handler before recording its successful outcome.
                        result = route.handler(body, query, context=context, **kwargs)
                    # Execute context-free handlers through their existing compatible signature.
                    else:
                        # Store the successful response for envelope return and safe event classification.
                        result = route.handler(body, query, **kwargs)
                # Preserve published Casino errors after recording only their sanitized category.
                except CasinoError as error:
                    # Record the fixed error code and coarse elapsed bucket for guest game requests.
                    _record_guest_game_error(context, path, error.code if error.code in guest_analytics.ALLOWED_ERROR_CATEGORIES else "SERVER_ERROR", (time.perf_counter() - started_at) * 1000)
                    # Re-raise the original error without changing its envelope.
                    raise
                # Preserve unexpected failures after recording one generic category.
                except Exception:
                    # Record no exception message, type, path value, or stack detail.
                    _record_guest_game_error(context, path, "SERVER_ERROR", (time.perf_counter() - started_at) * 1000)
                    # Re-raise for the existing sanitized adapter error boundary.
                    raise
                # Record game telemetry only after the handler succeeds and only for a guest principal.
                if path.startswith("/api/v1/games/"):
                    # Classify the successful request using route shape, coarse latency, and authoritative ledger differences.
                    _record_guest_game_event(context, method, path, result, (time.perf_counter() - started_at) * 1000, ledger_before)
                # Return the original handler response unchanged.
                return result
        # Raise an error so invalid input or state is reported explicitly.
        raise NotFoundError(f"No route for {method} {path}")
