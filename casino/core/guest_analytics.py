# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""De-identified, retention-bounded guest-trial analytics for restricted-preview Admin use."""

# Import date arithmetic for raw and aggregate retention enforcement.
from datetime import datetime, timedelta, timezone
# Import finite-number validation for fake-token aggregate safety.
import math

# Import the shared data root so telemetry stays in governed runtime state.
from casino.config import DATA_DIR, SCHEMA_VERSION
# Import the shared clock so lifecycle and analytics records use one format.
from casino.core.clock import utc_now
# Import the random id helper for identifiers unrelated to auth or player state.
from casino.core.ids import new_id
# Import atomic persistence so concurrent actions cannot lose de-identified counters.
from casino.core.state_store import read_json, update_json

# Store analytics separately from authentication, player, and ledger documents.
TRIALS_PATH = DATA_DIR / "analytics" / "guest_trials.json"
# Retain raw de-identified trial rows for no more than thirty days.
RAW_RETENTION_DAYS = 30
# Retain daily aggregate rows for the approved thirteen-month reporting window.
AGGREGATE_RETENTION_DAYS = 400
# Bound raw rows defensively even when a cleanup schedule is delayed.
MAX_TRIALS = 5_000
# Suppress pure activity writes when a recent request already refreshed the marker.
TOUCH_MIN_SECONDS = 60
# Enumerate the only event categories persisted from guest activity.
ALLOWED_EVENTS = frozenset({"activity", "lobby_reached", "game_open", "game_action", "game_error", "account_cta_viewed", "account_cta_selected"})
# Enumerate lifecycle reasons safe for Admin reporting.
ALLOWED_END_REASONS = frozenset({"ended", "expired", "inactive", "browser_closed", "revoked", "converted"})
# Enumerate locale values accepted into analytics dimensions.
ALLOWED_LOCALES = frozenset({"en-US", "ru-RU"})
# Enumerate coarse device values that cannot fingerprint a browser.
ALLOWED_DEVICES = frozenset({"mobile", "tablet", "desktop", "unknown"})
# Enumerate lifecycle filters published by the Admin contract.
ALLOWED_STATUSES = frozenset({"active", "ended", "expired"})
# Enumerate completion filters published by the Admin contract.
ALLOWED_COMPLETION_FILTERS = frozenset({"yes", "no"})
# Enumerate sanitized error categories that never retain exception messages.
ALLOWED_ERROR_CATEGORIES = frozenset({"VALIDATION_ERROR", "INSUFFICIENT_FUNDS", "CONFLICT", "FORBIDDEN", "NOT_FOUND", "RATE_LIMITED", "SERVER_ERROR"})
# Enumerate low-cardinality latency buckets used instead of precise request timings.
ALLOWED_LATENCY_BUCKETS = frozenset({"under_100ms", "100_499ms", "500_1999ms", "2000ms_plus"})
# Enumerate route-authored action categories accepted into product telemetry.
ALLOWED_ACTION_CATEGORIES = frozenset({"rounds", "rolls", "spins", "spin", "cards", "scratches", "tickets", "draw", "drops", "plays", "bets", "deal", "hands", "actions", "hit", "stand", "double", "split", "surrender", "insurance", "even-money", "holds", "play", "pass", "call", "fold", "war", "raise", "decision", "decisions", "guesses", "first-decision", "second-decision", "auto", "reset", "rebet", "clear", "settings", "other"})
# Identify action categories that authoritatively begin a round or one-step play.
ROUND_START_ACTIONS = frozenset({"rounds", "rolls", "spins", "spin", "cards", "tickets", "drops", "plays", "deal", "hands", "draw"})
# Bound each retained allowlisted event timeline independently from raw-row retention.
MAX_TIMELINE_EVENTS = 80
# Require a small cohort before exposing locale/device error breakdowns.
PRIVACY_COHORT_MINIMUM = 5

# Build the canonical empty telemetry document.
def default_trials() -> dict:
    # Return schema metadata, raw rows, daily aggregates, and cleanup health without identifiers.
    return {"schema_version": SCHEMA_VERSION, "trials": [], "daily": [], "cleanup": {"last_success_at": None, "last_failure_at": None, "last_error": None, "raw_retention_days": RAW_RETENTION_DAYS, "aggregate_retention_days": AGGREGATE_RETENTION_DAYS}}

# Parse one stored ISO timestamp into an aware datetime.
def _parse(value: str) -> datetime:
    # Convert the shared Z suffix into the offset syntax accepted by the standard parser.
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

# Normalize a client-provided locale into one approved low-cardinality dimension.
def _locale(value: str) -> str:
    # Keep the exact supported locale or use the default without persisting arbitrary text.
    return value if value in ALLOWED_LOCALES else "en-US"

# Normalize a client-provided device class into one approved low-cardinality dimension.
def _device(value: str) -> str:
    # Keep the exact supported class or collapse unknown input to the safe sentinel.
    return value if value in ALLOWED_DEVICES else "unknown"

# Normalize one action category derived only from a registered server route.
def action_category(path_segments) -> str:
    # Accept either one category or a route-tail collection without retaining identifiers.
    candidates = [path_segments] if isinstance(path_segments, str) else list(path_segments or [])
    # Walk from the route leaf toward the game root to skip dynamic round identifiers.
    for candidate in reversed(candidates):
        # Normalize the server-owned segment into its exact low-cardinality spelling.
        normalized = str(candidate or "").strip().lower()
        # Return only an explicitly allowlisted action name.
        if normalized in ALLOWED_ACTION_CATEGORIES:
            # Preserve the matched route-authored category.
            return normalized
    # Collapse unrecognized route shapes to the safe aggregate bucket.
    return "other"

# Report whether a route-authored action begins a round for aggregate accounting.
def starts_round(category: str) -> bool:
    # Check only the normalized allowlist rather than caller-authored request values.
    return action_category(category) in ROUND_START_ACTIONS

# Convert one request duration into a coarse latency bucket.
def latency_bucket(milliseconds) -> str:
    # Start protected numeric parsing so malformed instrumentation never blocks gameplay.
    try:
        # Normalize finite non-negative latency without retaining a precise timing.
        value = max(0.0, float(milliseconds))
    # Collapse absent or malformed instrumentation to the broadest safe bucket.
    except (TypeError, ValueError):
        # Use the first bucket for tests and callers that cannot measure latency.
        return "under_100ms"
    # Return the configured low-cardinality bucket.
    if value < 100:
        # Classify fast requests.
        return "under_100ms"
    # Return the moderate request bucket.
    if value < 500:
        # Classify requests below half a second.
        return "100_499ms"
    # Return the slow request bucket.
    if value < 2000:
        # Classify requests below two seconds.
        return "500_1999ms"
    # Collapse all longer timings into one bounded category.
    return "2000ms_plus"

# Normalize one fake-token aggregate without accepting NaN, infinity, or extreme expansion.
def _amount(value) -> float:
    # Start protected conversion because telemetry must never break authoritative settlement.
    try:
        # Convert numeric ledger totals into the JSON-compatible float shape.
        amount = float(value or 0)
    # Treat missing or malformed instrumentation as zero.
    except (TypeError, ValueError):
        # Return no aggregate contribution.
        return 0.0
    # Reject non-finite or unexpectedly large instrumentation before persistence.
    if not math.isfinite(amount) or abs(amount) > 1_000_000_000_000:
        # Return no aggregate contribution.
        return 0.0
    # Preserve ledger precision for fake-token summaries.
    return round(max(0.0, amount), 2)

# Build the complete nine-stage funnel defaults for one retained row.
def _milestones() -> dict:
    # Return only approved boolean journey states with no free-form client data.
    return {"landing_viewed": True, "trial_started": True, "lobby_reached": False, "first_game_opened": False, "first_action_accepted": False, "first_round_completed": False, "second_game_opened": False, "trial_terminal": False, "account_cta_viewed": False, "account_cta_selected": False}

# Build one canonical per-game aggregate row.
def _game_row() -> dict:
    # Return bounded counters and category maps without round or player identifiers.
    return {"opens": 0, "actions": 0, "rounds_started": 0, "rounds_completed": 0, "rounds_abandoned": 0, "errors": 0, "wagered": 0.0, "returned": 0.0, "net": 0.0, "first_action_ms": None, "action_categories": {}, "error_categories": {}, "latency_buckets": {}}

# Normalize one game slug without accepting paths, query values, or arbitrary payload text.
def _game(value: str) -> str:
    # Retain only bounded lowercase identifier characters used by registered game routes.
    normalized = "".join(character for character in str(value or "").lower() if character.isalnum() or character in ("_", "-"))
    # Cap the dimension length so hostile paths cannot expand telemetry documents.
    return normalized[:64]

# Return a canonical telemetry container for any malformed legacy document.
def _normalize(state: dict) -> dict:
    # Replace non-object or row-less state with the current empty schema.
    if not isinstance(state, dict) or not isinstance(state.get("trials"), list):
        # Return a new document rather than attempting to repair unknown data in place.
        return default_trials()
    # Add aggregate and cleanup containers introduced after the first guest-trial draft.
    state.setdefault("daily", [])
    # Add cleanup health without overwriting an earlier successful run.
    state.setdefault("cleanup", default_trials()["cleanup"])
    # Upgrade each retained draft row to the complete bounded analytics schema.
    for trial in state.get("trials", []):
        # Add the approved journey state while preserving any previously reached milestones.
        stored_milestones = trial.setdefault("milestones", {})
        # Supply every current funnel stage while preserving previously reached states.
        for milestone, reached in _milestones().items():
            # Preserve any stored boolean and add only missing current-schema stages.
            stored_milestones.setdefault(milestone, reached)
        # Add aggregate counters introduced by the complete Admin acceptance contract.
        for key, default in (("entry_surface", "auth"), ("starting_balance", 5000.0), ("ending_balance", None), ("rounds_started", 0), ("rounds_abandoned", 0), ("errors", 0), ("wagered", 0.0), ("returned", 0.0), ("net", 0.0), ("error_categories", {}), ("latency_buckets", {}), ("events", [])):
            # Preserve an existing value while supplying current-schema defaults.
            trial.setdefault(key, default)
        # Upgrade every retained game counter without adding identifiers.
        for counters in trial.setdefault("games", {}).values():
            # Supply each current per-game aggregate field independently.
            for key, default in _game_row().items():
                # Preserve existing draft counters where present.
                counters.setdefault(key, default)
    # Stamp the current storage schema for downstream validation.
    state["schema_version"] = SCHEMA_VERSION
    # Return the normalized mutable document.
    return state

# Record the start of one guest trial and return its de-identified analytics id.
def record_started(locale: str = "en-US", device: str = "unknown", starting_balance: float = 10000.0) -> str:
    # Mint an identifier unrelated to user, player, session, network, or browser credentials.
    analytics_id = new_id("gtrial")
    # Capture one timestamp for both the start and first activity marker.
    now = utc_now()
    # Define the atomic append of one safe raw row.
    def mutate(state: dict) -> dict:
        # Normalize the document before appending current-schema fields.
        state = _normalize(state)
        # Append only low-cardinality dimensions, fake-token aggregates, milestones, and an allowlisted timeline.
        state["trials"].append({"analytics_id": analytics_id, "started_at": now, "last_event_at": now, "ended_at": None, "end_reason": None, "duration_seconds": None, "locale": _locale(locale), "device": _device(device), "entry_surface": "auth", "starting_balance": _amount(starting_balance), "ending_balance": None, "engaged": False, "rounds_started": 0, "rounds_completed": 0, "rounds_abandoned": 0, "actions": 0, "errors": 0, "wagered": 0.0, "returned": 0.0, "net": 0.0, "error_categories": {}, "latency_buckets": {}, "milestones": _milestones(), "games": {}, "events": [{"at": now, "event": "trial_started"}]})
        # Retain the newest bounded set until scheduled cleanup applies the time window.
        state["trials"] = state["trials"][-MAX_TRIALS:]
        # Return the mutated document for atomic persistence.
        return state
    # Persist the row without writing any credential or identity pointer.
    update_json(TRIALS_PATH, mutate, default_trials)
    # Return the one-way analytics identifier for binding on the disposable user only.
    return analytics_id

# Record one server-observed, allowlisted guest event.
def record_event(analytics_id: str, event: str = "activity", game: str = "", action: str = "", latency_ms=None, error_category: str = "", wagered=0, returned=0, round_started: bool = False, round_completed: bool = False) -> None:
    # Ignore calls without the one-way analytics binding.
    if not analytics_id:
        # Return without touching the analytics document.
        return
    # Collapse unknown event text to a pure activity touch.
    safe_event = event if event in ALLOWED_EVENTS else "activity"
    # Normalize the optional registered-game dimension.
    safe_game = _game(game)
    # Normalize a server-route action into the fixed published category set.
    safe_action = action_category(action)
    # Normalize any server exception into the published category set without retaining its message.
    safe_error = error_category if error_category in ALLOWED_ERROR_CATEGORIES else ("SERVER_ERROR" if safe_event == "game_error" else "")
    # Convert precise elapsed time into one low-cardinality bucket.
    safe_latency = latency_bucket(latency_ms) if safe_event in ("game_open", "game_action", "game_error") else ""
    # Normalize authoritative ledger totals to fake-token precision.
    safe_wagered = _amount(wagered)
    # Normalize authoritative returned credits separately from wager debits.
    safe_returned = _amount(returned)
    # Capture the observation instant once.
    now = utc_now()
    # Define the atomic counter update.
    def mutate(state: dict) -> dict:
        # Normalize the document before walking raw rows.
        state = _normalize(state)
        # Find the matching open trial without referencing auth storage.
        for trial in state["trials"]:
            # Update only the requested active analytics row.
            if trial.get("analytics_id") == analytics_id and not trial.get("ended_at"):
                # Determine whether a pure touch is recent enough to suppress.
                recent_touch = (_parse(now) - _parse(trial.get("last_event_at") or trial.get("started_at"))).total_seconds() < TOUCH_MIN_SECONDS
                # Refresh activity for material events or stale pure touches.
                if safe_event != "activity" or not recent_touch:
                    # Update the server-observed activity marker.
                    trial["last_event_at"] = now
                # Read the canonical journey milestone map.
                milestones = trial.setdefault("milestones", _milestones())
                # Mark the lobby milestone only after the authenticated current-user route succeeds.
                if safe_event == "lobby_reached":
                    # Record the first authenticated shell entry.
                    milestones["lobby_reached"] = True
                # Mark the engagement milestone on the first game surface or action.
                if safe_event in ("game_open", "game_action"):
                    # Persist a boolean milestone rather than a navigation history.
                    trial["engaged"] = True
                    # Record first-game entry for the published funnel.
                    milestones["first_game_opened"] = True
                # Count state-changing game requests as aggregate actions.
                if safe_event == "game_action":
                    # Increment the bounded integer action counter.
                    trial["actions"] = int(trial.get("actions") or 0) + 1
                    # Mark the first server-accepted action milestone.
                    milestones["first_action_accepted"] = True
                # Count server-classified round starts when supplied by the router.
                if round_started:
                    # Increment the aggregate start counter independently from action count.
                    trial["rounds_started"] = int(trial.get("rounds_started") or 0) + 1
                # Count explicit completed-round classifications when supplied by the router.
                if round_completed:
                    # Increment the bounded round-completion counter.
                    trial["rounds_completed"] = int(trial.get("rounds_completed") or 0) + 1
                    # Mark the first authoritative terminal result milestone.
                    milestones["first_round_completed"] = True
                # Mark the post-trial account journey view without inferring identity linkage.
                if safe_event == "account_cta_viewed":
                    # Record only the allowlisted view milestone.
                    milestones["account_cta_viewed"] = True
                # Mark an explicitly instrumented account journey selection without storing target identity.
                if safe_event == "account_cta_selected":
                    # Record only the allowlisted selection milestone.
                    milestones["account_cta_selected"] = True
                # Count sanitized server error categories independently from successful actions.
                if safe_event == "game_error":
                    # Increment the total error counter.
                    trial["errors"] = int(trial.get("errors") or 0) + 1
                    # Increment the bounded category counter.
                    trial.setdefault("error_categories", {})[safe_error] = int(trial.setdefault("error_categories", {}).get(safe_error) or 0) + 1
                # Aggregate fake-token ledger movement only from successful game actions.
                if safe_event == "game_action":
                    # Add authoritative wager debits.
                    trial["wagered"] = round(float(trial.get("wagered") or 0) + safe_wagered, 2)
                    # Add authoritative returned credits.
                    trial["returned"] = round(float(trial.get("returned") or 0) + safe_returned, 2)
                    # Derive net change from the two independently accumulated aggregates.
                    trial["net"] = round(float(trial.get("returned") or 0) - float(trial.get("wagered") or 0), 2)
                # Count every measured request inside its low-cardinality latency bucket.
                if safe_latency:
                    # Increment the request bucket without storing precise elapsed time.
                    trial.setdefault("latency_buckets", {})[safe_latency] = int(trial.setdefault("latency_buckets", {}).get(safe_latency) or 0) + 1
                # Count per-game activity only for a normalized registered-game slug.
                if safe_game and safe_event in ("game_open", "game_action", "game_error"):
                    # Read or create the compact aggregate for this game.
                    game_row = trial.setdefault("games", {}).setdefault(safe_game, _game_row())
                    # Increment the relevant open counter.
                    if safe_event == "game_open":
                        # Count one server-observed surface open.
                        game_row["opens"] += 1
                    # Increment the relevant action counter.
                    if safe_event == "game_action":
                        # Count one server-observed game mutation.
                        game_row["actions"] += 1
                        # Increment the bounded server-route action category.
                        game_row.setdefault("action_categories", {})[safe_action] = int(game_row.setdefault("action_categories", {}).get(safe_action) or 0) + 1
                        # Capture only the first-action duration for median aggregation, never every precise latency.
                        if game_row.get("first_action_ms") is None:
                            # Derive elapsed milliseconds from server timestamps.
                            game_row["first_action_ms"] = max(0, int((_parse(now) - _parse(trial.get("started_at") or now)).total_seconds() * 1000))
                    # Count round starts separately from generic actions.
                    if round_started:
                        # Increment the game's aggregate started rounds.
                        game_row["rounds_started"] += 1
                    # Increment the relevant completion counter.
                    if round_completed:
                        # Count one server-classified completed round.
                        game_row["rounds_completed"] += 1
                    # Count sanitized game failures without retaining request values or messages.
                    if safe_event == "game_error":
                        # Increment the game error total.
                        game_row["errors"] += 1
                        # Increment the game's error category.
                        game_row.setdefault("error_categories", {})[safe_error] = int(game_row.setdefault("error_categories", {}).get(safe_error) or 0) + 1
                    # Aggregate successful ledger movement at the game dimension.
                    if safe_event == "game_action":
                        # Add fake-token wagers from authoritative ledger debits.
                        game_row["wagered"] = round(float(game_row.get("wagered") or 0) + safe_wagered, 2)
                        # Add fake-token returns from authoritative ledger credits.
                        game_row["returned"] = round(float(game_row.get("returned") or 0) + safe_returned, 2)
                        # Derive game net from accumulated returns minus wagers.
                        game_row["net"] = round(float(game_row.get("returned") or 0) - float(game_row.get("wagered") or 0), 2)
                    # Count the coarse game-request latency bucket.
                    if safe_latency:
                        # Increment the bounded latency category.
                        game_row.setdefault("latency_buckets", {})[safe_latency] = int(game_row.setdefault("latency_buckets", {}).get(safe_latency) or 0) + 1
                    # Mark second-game reach only after two distinct registered slugs exist.
                    if len(trial.get("games", {})) >= 2:
                        # Record the published second-game funnel milestone.
                        milestones["second_game_opened"] = True
                # Select the single allowlisted timeline event name for this observation.
                timeline_event = "round_completed" if round_completed else ("round_started" if round_started else safe_event)
                # Build an identifier-free event row from approved fields only.
                timeline_row = {"at": now, "event": timeline_event}
                # Include the registered game slug when present.
                if safe_game:
                    # Add only the normalized catalog key.
                    timeline_row["game"] = safe_game
                # Include the route-authored category for game mutations and failures.
                if safe_event in ("game_action", "game_error"):
                    # Add only the allowlisted action category.
                    timeline_row["action_category"] = safe_action
                # Include the sanitized error category only on failures.
                if safe_error:
                    # Add only the enumerated error code.
                    timeline_row["error_category"] = safe_error
                # Include the coarse latency bucket only for measured game requests.
                if safe_latency:
                    # Add no precise request duration.
                    timeline_row["latency_bucket"] = safe_latency
                # Retain only the newest bounded allowlisted timeline.
                trial.setdefault("events", []).append(timeline_row)
                # Apply the per-row timeline bound after every append.
                trial["events"] = trial["events"][-MAX_TIMELINE_EVENTS:]
        # Return the mutated document for atomic persistence.
        return state
    # Persist the allowlisted aggregate event atomically.
    update_json(TRIALS_PATH, mutate, default_trials)

# Record the irreversible end of one guest trial with a bounded reason.
def record_ended(analytics_id: str, reason: str = "ended", ending_balance=None) -> None:
    # Ignore callers without a bound analytics id.
    if not analytics_id:
        # Return without touching the analytics document.
        return
    # Normalize the lifecycle reason without retaining arbitrary exception text.
    safe_reason = reason if reason in ALLOWED_END_REASONS else "ended"
    # Capture the end instant for duration math.
    now = utc_now()
    # Define the atomic close mutation.
    def mutate(state: dict) -> dict:
        # Normalize the document before walking raw rows.
        state = _normalize(state)
        # Find the matching open trial.
        for trial in state["trials"]:
            # Close the requested analytics row exactly once.
            if trial.get("analytics_id") == analytics_id and not trial.get("ended_at"):
                # Stamp the irreversible end time.
                trial["ended_at"] = now
                # Store only the bounded lifecycle reason.
                trial["end_reason"] = safe_reason
                # Calculate the whole-second duration from server timestamps.
                trial["duration_seconds"] = max(0, int((_parse(now) - _parse(trial.get("started_at") or now)).total_seconds()))
                # Align last activity to the lifecycle end for stable reporting.
                trial["last_event_at"] = now
                # Preserve the terminal fake-token balance as a de-identified product aggregate.
                trial["ending_balance"] = _amount(ending_balance) if ending_balance is not None else trial.get("ending_balance")
                # Mark the terminal journey state for the full funnel.
                trial.setdefault("milestones", _milestones())["trial_terminal"] = True
                # Show the account journey only after an explicit user end, never by inferring identity.
                if safe_reason == "ended":
                    # Record that the returned auth surface includes the sign-in/start-again choices.
                    trial["milestones"]["account_cta_viewed"] = True
                # Compute abandoned rounds from starts without terminal completion.
                trial["rounds_abandoned"] = max(0, int(trial.get("rounds_started") or 0) - int(trial.get("rounds_completed") or 0))
                # Finalize each per-game abandoned-round aggregate.
                for game_row in trial.get("games", {}).values():
                    # Preserve only a non-negative aggregate count.
                    game_row["rounds_abandoned"] = max(0, int(game_row.get("rounds_started") or 0) - int(game_row.get("rounds_completed") or 0))
                # Append one bounded lifecycle event without identity or credential fields.
                trial.setdefault("events", []).append({"at": now, "event": "trial_terminal", "reason": safe_reason})
                # Apply the same timeline bound to terminal records.
                trial["events"] = trial["events"][-MAX_TIMELINE_EVENTS:]
        # Return the mutated document for atomic persistence.
        return state
    # Persist the closed summary atomically.
    update_json(TRIALS_PATH, mutate, default_trials)

# Apply raw and aggregate retention and publish identifier-free cleanup health.
def cleanup() -> dict:
    # Capture one cutoff basis for a deterministic run.
    now = datetime.now(timezone.utc)
    # Create result counters outside the mutation for the Admin acknowledgement.
    result = {"raw_removed": 0, "aggregate_removed": 0, "completed_at": None}
    # Define the atomic retention mutation.
    def mutate(state: dict) -> dict:
        # Normalize the document before applying retention.
        state = _normalize(state)
        # Calculate the oldest permitted raw-row timestamp.
        raw_cutoff = now - timedelta(days=RAW_RETENTION_DAYS)
        # Calculate the oldest permitted daily aggregate date.
        aggregate_cutoff = (now - timedelta(days=AGGREGATE_RETENTION_DAYS)).date()
        # Split expired raw rows for aggregation before deletion.
        expired = [trial for trial in state["trials"] if _parse(trial.get("started_at")) < raw_cutoff]
        # Retain only raw rows inside the approved window.
        state["trials"] = [trial for trial in state["trials"] if _parse(trial.get("started_at")) >= raw_cutoff]
        # Report the exact number of removed raw rows.
        result["raw_removed"] = len(expired)
        # Build a date-keyed lookup over existing aggregate rows.
        daily = {row.get("date"): row for row in state.get("daily", []) if row.get("date")}
        # Fold each expired raw row into non-identifying daily counters.
        for trial in expired:
            # Derive the UTC calendar date from the server start timestamp.
            day = _parse(trial["started_at"]).date().isoformat()
            # Read or create the aggregate dimensions and counters.
            row = daily.setdefault(day, {"date": day, "started": 0, "lobby_reached": 0, "engaged": 0, "actions": 0, "rounds_started": 0, "rounds_completed": 0, "rounds_abandoned": 0, "errors": 0, "wagered": 0.0, "returned": 0.0, "net": 0.0, "ended": 0})
            # Count the expired raw trial once.
            row["started"] += 1
            # Count whether the trial reached the authenticated lobby.
            row["lobby_reached"] = int(row.get("lobby_reached") or 0) + (1 if trial.get("milestones", {}).get("lobby_reached") else 0)
            # Count whether it reached the engagement milestone.
            row["engaged"] += 1 if trial.get("engaged") else 0
            # Add its completed-round aggregate.
            row["rounds_completed"] += int(trial.get("rounds_completed") or 0)
            # Add accepted action, started, abandoned, and error aggregates.
            row["actions"] = int(row.get("actions") or 0) + int(trial.get("actions") or 0)
            # Add server-classified round starts.
            row["rounds_started"] = int(row.get("rounds_started") or 0) + int(trial.get("rounds_started") or 0)
            # Add terminally abandoned round estimates.
            row["rounds_abandoned"] = int(row.get("rounds_abandoned") or 0) + int(trial.get("rounds_abandoned") or 0)
            # Add sanitized server-error totals.
            row["errors"] = int(row.get("errors") or 0) + int(trial.get("errors") or 0)
            # Add fake-token ledger debits to daily totals.
            row["wagered"] = round(float(row.get("wagered") or 0) + float(trial.get("wagered") or 0), 2)
            # Add fake-token ledger credits to daily totals.
            row["returned"] = round(float(row.get("returned") or 0) + float(trial.get("returned") or 0), 2)
            # Derive daily net from its accumulated return and wager totals.
            row["net"] = round(float(row.get("returned") or 0) - float(row.get("wagered") or 0), 2)
            # Count whether it reached any terminal lifecycle state.
            row["ended"] += 1 if trial.get("ended_at") else 0
        # Keep aggregate dates only inside the approved thirteen-month window.
        retained_daily = [row for day, row in daily.items() if datetime.fromisoformat(day).date() >= aggregate_cutoff]
        # Report the number of aggregate rows removed by retention.
        result["aggregate_removed"] = len(daily) - len(retained_daily)
        # Store aggregates in stable chronological order.
        state["daily"] = sorted(retained_daily, key=lambda row: row["date"])
        # Capture the successful run timestamp.
        completed_at = utc_now()
        # Publish success health without paths or exception details.
        state["cleanup"] = {"last_success_at": completed_at, "last_failure_at": state.get("cleanup", {}).get("last_failure_at"), "last_error": None, "raw_retention_days": RAW_RETENTION_DAYS, "aggregate_retention_days": AGGREGATE_RETENTION_DAYS}
        # Reflect the timestamp in the route result.
        result["completed_at"] = completed_at
        # Return the mutated document for atomic persistence.
        return state
    # Start protected persistence so a failed cleanup remains observable to Admin.
    try:
        # Persist retention atomically; successful runs clear any prior sanitized failure marker.
        update_json(TRIALS_PATH, mutate, default_trials)
    # Record only a bounded failure category before preserving the original standard error path.
    except Exception:
        # Capture a server timestamp without retaining exception text, paths, or identifiers.
        failed_at = utc_now()
        # Define a best-effort health-only mutation that does not parse malformed telemetry rows.
        def mark_failure(state: dict) -> dict:
            # Normalize only the document containers required for cleanup health.
            state = _normalize(state)
            # Preserve the last successful run while publishing a sanitized failure marker.
            state["cleanup"] = {"last_success_at": state.get("cleanup", {}).get("last_success_at"), "last_failure_at": failed_at, "last_error": "cleanup_failed", "raw_retention_days": RAW_RETENTION_DAYS, "aggregate_retention_days": AGGREGATE_RETENTION_DAYS}
            # Return the health-marked document for best-effort persistence.
            return state
        # Start a separate best-effort write because a completely unavailable store cannot record its own outage.
        try:
            # Persist the bounded health marker without changing retention scope or caller-selected paths.
            update_json(TRIALS_PATH, mark_failure, default_trials)
        # Preserve the original failure when even the health write cannot reach storage.
        except Exception:
            # Intentionally do not replace the original sanitized API failure.
            pass
        # Re-raise so the cleanup mutation never reports a false success.
        raise
    # Return identifier-free cleanup counts and health.
    return result

# Return one de-identified raw row by its analytics id for an Admin detail route.
def detail(analytics_id: str) -> dict | None:
    # Read the telemetry snapshot without mutating lifecycle state.
    state = _normalize(read_json(TRIALS_PATH, default_trials))
    # Find the requested analytics-only row.
    for trial in state["trials"]:
        # Return a copy so route formatting cannot mutate storage.
        if trial.get("analytics_id") == analytics_id:
            # Copy the row without any authentication or player identifiers because none are stored.
            return dict(trial)
    # Return no result when retention removed the row or the id never existed.
    return None

# Calculate a numeric median without exposing raw rows outside the Admin response.
def _median(values) -> float:
    # Sort finite numeric values once for deterministic midpoint selection.
    ordered = sorted(float(value) for value in values if isinstance(value, (int, float)) and math.isfinite(float(value)))
    # Return zero when no completed metric exists.
    if not ordered:
        # Use a stable JSON number rather than null in summary cards.
        return 0.0
    # Locate the midpoint in the sorted values.
    middle = len(ordered) // 2
    # Return the center value for an odd-length set.
    if len(ordered) % 2:
        # Preserve two-decimal reporting precision.
        return round(ordered[middle], 2)
    # Average the two center values for an even-length set.
    return round((ordered[middle - 1] + ordered[middle]) / 2, 2)

# Add one bounded category map into another.
def _add_counts(target: dict, source: dict) -> None:
    # Walk only stored mapping items because category keys were normalized before persistence.
    for key, value in (source or {}).items():
        # Increment the integer aggregate without copying any raw event content.
        target[key] = int(target.get(key) or 0) + int(value or 0)

# Build the Admin summary, funnel, games, recent rows, and cleanup status.
def summary(active_window_seconds: int = 300, recent_limit: int = 25, locale: str = "", device: str = "", status: str = "", game: str = "", completed: str = "", error_category: str = "", since: str = "", until: str = "") -> dict:
    # Start protected retention so a recorded cleanup failure remains visible on a readable store.
    try:
        # Apply retention before every Admin read so delayed schedulers cannot exceed the governed windows.
        cleanup()
    # Continue only to the bounded health/read path after cleanup recorded its sanitized failure marker.
    except Exception:
        # Avoid masking the observable failure state with raw exception text.
        pass
    # Read the cleaned analytics document.
    state = _normalize(read_json(TRIALS_PATH, default_trials))
    # Start from all retained raw rows.
    trials = list(state["trials"])
    # Apply the optional allowlisted locale filter.
    if locale in ALLOWED_LOCALES:
        # Retain only rows with the selected locale.
        trials = [trial for trial in trials if trial.get("locale") == locale]
    # Apply the optional allowlisted device filter.
    if device in ALLOWED_DEVICES:
        # Retain only rows with the selected device class.
        trials = [trial for trial in trials if trial.get("device") == device]
    # Apply the optional lifecycle filter.
    if status == "active":
        # Retain only open rows.
        trials = [trial for trial in trials if not trial.get("ended_at")]
    # Apply the optional terminal lifecycle filter.
    if status == "ended":
        # Retain all terminal rows.
        trials = [trial for trial in trials if trial.get("ended_at")]
    # Apply the optional expiry-only lifecycle filter.
    if status == "expired":
        # Retain inactivity and absolute-expiry terminal rows.
        trials = [trial for trial in trials if trial.get("end_reason") in ("expired", "inactive")]
    # Normalize the optional registered-game filter without persisting query content.
    safe_game = _game(game)
    # Apply the game filter only when a normalized slug was supplied.
    if safe_game:
        # Retain trials whose bounded game map includes the selected game.
        trials = [trial for trial in trials if safe_game in trial.get("games", {})]
    # Apply the first-round completion filter.
    if completed in ALLOWED_COMPLETION_FILTERS:
        # Retain rows matching the requested boolean milestone.
        trials = [trial for trial in trials if bool(int(trial.get("rounds_completed") or 0)) == (completed == "yes")]
    # Apply the sanitized error-category filter.
    if error_category in ALLOWED_ERROR_CATEGORIES:
        # Retain rows with at least one matching server error.
        trials = [trial for trial in trials if int(trial.get("error_categories", {}).get(error_category) or 0) > 0]
    # Apply the lower time bound when the trusted Admin layer supplied a validated ISO timestamp.
    if since:
        # Retain trials starting on or after the inclusive bound.
        trials = [trial for trial in trials if _parse(trial.get("started_at")) >= _parse(since)]
    # Apply the upper time bound when the trusted Admin layer supplied a validated ISO timestamp.
    if until:
        # Retain trials starting on or before the inclusive bound.
        trials = [trial for trial in trials if _parse(trial.get("started_at")) <= _parse(until)]
    # Capture one comparison instant for the active-now window.
    now = _parse(utc_now())
    # Count open rows with recent server activity.
    active_now = sum(1 for trial in trials if not trial.get("ended_at") and (now - _parse(trial.get("last_event_at") or trial.get("started_at"))).total_seconds() <= active_window_seconds)
    # Calculate the complete named funnel from server-observed boolean milestones.
    funnel = {key: sum(1 for trial in trials if trial.get("milestones", {}).get(key)) for key in _milestones()}
    # Preserve the original compact keys for compatible Admin clients.
    funnel.update({"started": funnel["trial_started"], "engaged": funnel["first_game_opened"], "completed_round": funnel["first_round_completed"]})
    # Calculate rates against trial starts without division errors.
    funnel_rates = {key: round((value / funnel["trial_started"] * 100), 1) if funnel["trial_started"] else 0.0 for key, value in funnel.items() if key not in ("started", "engaged", "completed_round")}
    # Build aggregate per-game counters from retained rows.
    games = {}
    # Walk every filtered trial's compact game map.
    for trial in trials:
        # Walk each registered game dimension and its safe counters.
        for game_slug, counters in trial.get("games", {}).items():
            # Respect the selected game filter in the aggregate table.
            if safe_game and game_slug != safe_game:
                # Skip every non-selected registered game.
                continue
            # Read or create the complete summary counter row.
            target = games.setdefault(game_slug, {"game": game_slug, "trials": 0, "opens": 0, "actions": 0, "rounds_started": 0, "rounds_completed": 0, "rounds_abandoned": 0, "errors": 0, "wagered": 0.0, "returned": 0.0, "net": 0.0, "first_action_samples": [], "action_categories": {}, "error_categories": {}, "latency_buckets": {}, "locale_errors": {}, "device_errors": {}})
            # Count this trial once for the game.
            target["trials"] += 1
            # Add integer event and round aggregates.
            for key in ("opens", "actions", "rounds_started", "rounds_completed", "rounds_abandoned", "errors"):
                # Increment the requested aggregate counter.
                target[key] += int(counters.get(key) or 0)
            # Add fake-token wager and return aggregates.
            target["wagered"] = round(target["wagered"] + float(counters.get("wagered") or 0), 2)
            # Add returned fake tokens.
            target["returned"] = round(target["returned"] + float(counters.get("returned") or 0), 2)
            # Derive net from accumulated totals.
            target["net"] = round(target["returned"] - target["wagered"], 2)
            # Collect one first-action duration sample per trial/game when present.
            if counters.get("first_action_ms") is not None:
                # Append the numeric duration for later median calculation.
                target["first_action_samples"].append(counters.get("first_action_ms"))
            # Merge route-authored action categories.
            _add_counts(target["action_categories"], counters.get("action_categories", {}))
            # Merge sanitized error categories.
            _add_counts(target["error_categories"], counters.get("error_categories", {}))
            # Merge low-cardinality latency buckets.
            _add_counts(target["latency_buckets"], counters.get("latency_buckets", {}))
            # Count locale errors for cohort-thresholded responsive diagnostics.
            if int(counters.get("errors") or 0):
                # Add only the supported locale dimension.
                target["locale_errors"][trial.get("locale")] = int(target["locale_errors"].get(trial.get("locale")) or 0) + int(counters.get("errors") or 0)
                # Add only the coarse device dimension.
                target["device_errors"][trial.get("device")] = int(target["device_errors"].get(trial.get("device")) or 0) + int(counters.get("errors") or 0)
    # Finalize medians and privacy-thresholded dimensions for every game row.
    for target in games.values():
        # Replace raw first-action samples with their single summary median.
        target["median_first_action_ms"] = _median(target.pop("first_action_samples"))
        # Suppress locale breakdowns below the approved minimum cohort.
        target["locale_errors"] = {key: value for key, value in target["locale_errors"].items() if value >= PRIVACY_COHORT_MINIMUM}
        # Suppress device breakdowns below the approved minimum cohort.
        target["device_errors"] = {key: value for key, value in target["device_errors"].items() if value >= PRIVACY_COHORT_MINIMUM}
    # Read completed durations for summary averages and medians.
    durations = [int(trial.get("duration_seconds")) for trial in trials if trial.get("duration_seconds") is not None]
    # Calculate total successful and failed server-observed game requests.
    total_requests = sum(int(trial.get("actions") or 0) + int(trial.get("errors") or 0) for trial in trials)
    # Calculate the percentage of retained trials without a server-observed error.
    error_free_rate = round(sum(1 for trial in trials if int(trial.get("errors") or 0) == 0) / len(trials) * 100, 1) if trials else 0.0
    # Return the complete de-identified Admin reporting shape.
    return {"started_total": len(trials), "active_now": active_now, "ended_total": sum(1 for trial in trials if trial.get("ended_at")), "expired_total": sum(1 for trial in trials if trial.get("end_reason") in ("expired", "inactive")), "active_window_seconds": active_window_seconds, "funnel": funnel, "funnel_rates": funnel_rates, "metrics": {"average_duration_seconds": round(sum(durations) / len(durations), 2) if durations else 0.0, "median_duration_seconds": _median(durations), "average_games_per_trial": round(sum(len(trial.get("games", {})) for trial in trials) / len(trials), 2) if trials else 0.0, "average_rounds_per_trial": round(sum(int(trial.get("rounds_completed") or 0) for trial in trials) / len(trials), 2) if trials else 0.0, "error_free_rate_percent": error_free_rate, "request_count": total_requests, "wagered": round(sum(float(trial.get("wagered") or 0) for trial in trials), 2), "returned": round(sum(float(trial.get("returned") or 0) for trial in trials), 2), "net": round(sum(float(trial.get("net") or 0) for trial in trials), 2), "fake_tokens_only": True}, "games": sorted(games.values(), key=lambda row: (-row["trials"], row["game"])), "recent": list(reversed(trials[-max(1, min(int(recent_limit), 100)):])), "daily": list(state.get("daily", [])), "cleanup": dict(state.get("cleanup", {})), "filters": {"locale": locale if locale in ALLOWED_LOCALES else "", "device": device if device in ALLOWED_DEVICES else "", "status": status if status in ALLOWED_STATUSES else "", "game": safe_game, "completed": completed if completed in ALLOWED_COMPLETION_FILTERS else "", "error_category": error_category if error_category in ALLOWED_ERROR_CATEGORIES else "", "since": since, "until": until}}
