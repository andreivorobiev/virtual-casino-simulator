# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Challenge Points transitions with no wallet, route, or provider activation.

This issue #1091 foundation accepts only server-selected rules and canonical performance
facts. It returns immutable append candidates for a future atomic provider adapter; it
does not persist events, register games, publish endpoints, or move play tokens. Practice
transitions deliberately return no append candidates. Ranked transitions enforce the
three-start UTC-day limit and derive daily-best deltas from an append-only journal.
(CHALLENGE-001, CHALLENGE-002, CHALLENGE-003)
"""

# Import dataclass support for immutable provider-neutral transition values.
from dataclasses import dataclass
# Import UTC-aware time primitives for exact attempt-day ownership.
from datetime import datetime, timezone
# Import SHA-256 for canonical semantic retry fingerprints.
import hashlib
# Import canonical JSON encoding for provider-independent performance facts.
import json
# Import strict identity patterns without accepting arbitrary path or namespace text.
import re
# Import callable and mapping types for the internal versioned score-rule seam.
from collections.abc import Callable, Iterable, Mapping
from typing import Any

# Import stable application errors for bounded validation and retry conflicts.
from casino.errors import ConflictError, ValidationError


# Limit every ranked game to the product-approved daily start allowance.
RANKED_ATTEMPTS_PER_UTC_DAY = 3
# Bound every deterministic ranked score to the product-approved point interval.
MIN_POINTS = 0
MAX_POINTS = 1_000
# Name the only accepted validation outcome that can contribute points.
ACCEPTED = "accepted"
# Name the only terminal validation outcome that records no points.
REJECTED = "rejected"
# Enumerate closed-vocabulary event kinds used by the append-only journal.
EVENT_KINDS = frozenset({"started", "completed"})
# Enumerate closed-vocabulary terminal validation outcomes.
VALIDATION_OUTCOMES = frozenset({ACCEPTED, REJECTED})
# Permit stable lower-case module identities without allowing routes or traversal.
IDENTITY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
# Permit dotted numeric rule revisions chosen by trusted game modules.
RULES_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
# Require a complete lower-case SHA-256 digest for acknowledged action evidence.
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
# Require exact second-precision canonical UTC timestamps in provider records.
UTC_TIMESTAMP_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
# Require exact ISO calendar-day syntax in provider records.
UTC_DAY_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
# List fields a future provider adapter may serialize without wallet semantics.
EVENT_FIELDS = (
    "event_id",
    "player_id",
    "game_id",
    "run_id",
    "occurred_at",
    "utc_day",
    "season_id",
    "mode",
    "rules_version",
    "configuration_id",
    "commitment_id",
    "bot_strategy_json",
    "attempt_ordinal",
    "kind",
    "status",
    "performance_facts_json",
    "formula_inputs_json",
    "awarded_points",
    "counted_best_delta",
    "action_digest",
    "idempotency_key",
    "request_fingerprint",
    "validation_outcome",
)


# Return one exact non-empty identity without stringifying hostile objects.
def _identity(value, *, field: str, pattern: re.Pattern | None = None) -> str:
    # Reject non-string and padded values so retry semantics have one representation.
    if type(value) is not str or value != value.strip() or not value:
        # Publish only the fixed internal field name.
        raise ValidationError(f"{field} is invalid", {"field": field})
    # Apply the requested closed identity grammar when one exists.
    if pattern is not None and pattern.fullmatch(value) is None:
        # Reject unexpected namespaces before any append candidate is constructed.
        raise ValidationError(f"{field} is invalid", {"field": field})
    # Return the exact validated string used in fingerprints and receipts.
    return value


# Normalize one aware timestamp to canonical UTC second precision.
def _utc(value, *, field: str) -> str:
    # Require a real aware datetime so local clock interpretation never changes a day.
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        # Refuse naive or non-datetime inputs before attempt accounting.
        raise ValidationError(f"{field} must be timezone-aware", {"field": field})
    # Convert to UTC and discard subsecond noise from retry fingerprints.
    normalized = value.astimezone(timezone.utc).replace(microsecond=0)
    # Publish one stable RFC 3339 representation.
    return normalized.isoformat().replace("+00:00", "Z")


# Derive the immutable UTC-day owner from one canonical timestamp.
def _utc_day(timestamp: str) -> str:
    # Return the date prefix of the validated fixed RFC 3339 representation.
    return timestamp[:10]


# Require an opaque bounded idempotency key suitable for future durable storage.
def _idempotency_key(value) -> str:
    # Reuse the exact identity boundary before applying operation-key length limits.
    key = _identity(value, field="idempotency_key")
    # Reject undersized, oversized, or multiline keys without reflecting their value.
    if len(key) < 16 or len(key) > 200 or any(character in key for character in "\r\n"):
        # Keep the diagnostic stable across providers and routes.
        raise ValidationError("idempotency_key is invalid", {"field": "idempotency_key"})
    # Return the caller-stable key for exact replay lookup.
    return key


# Encode one JSON-compatible object canonically or reject ambiguous values.
def _canonical_json(value, *, field: str) -> str:
    # Serialize through a strict encoder that rejects NaN, infinity, and custom objects.
    try:
        # Sort mapping keys and remove whitespace for provider-independent bytes.
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    # Convert every unsupported or non-finite value into a stable validation failure.
    except (TypeError, ValueError):
        # Never reflect raw performance facts or formula inputs in the diagnostic.
        raise ValidationError(f"{field} is invalid", {"field": field}) from None


# Validate one already-canonical JSON object stored inside an immutable event.
def _canonical_mapping_json(value, *, field: str) -> str:
    # Require a non-empty JSON string rather than silently stringifying a mapping.
    if type(value) is not str or not value:
        # Reject missing audit evidence on terminal events.
        raise ValidationError(f"{field} is invalid", {"field": field})
    # Decode only strict JSON without evaluating source text.
    try:
        # Parse the stored representation once for shape and canonical-byte checks.
        decoded = json.loads(value)
    # Convert malformed JSON to one bounded validation result.
    except (TypeError, ValueError):
        # Never reflect the malformed stored bytes.
        raise ValidationError(f"{field} is invalid", {"field": field}) from None
    # Require a mapping because performance facts and formula inputs have named fields.
    if not isinstance(decoded, dict):
        # Reject arrays and scalars before projection.
        raise ValidationError(f"{field} is invalid", {"field": field})
    # Require exact canonical bytes so equivalent values cannot carry multiple fingerprints.
    if _canonical_json(decoded, field=field) != value:
        # Refuse noncanonical whitespace, key ordering, or number encodings.
        raise ValidationError(f"{field} is not canonical", {"field": field})
    # Return the validated canonical representation unchanged.
    return value


# Validate one canonical UTC timestamp already stored in an event.
def _stored_utc(value, *, field: str) -> str:
    # Require the fixed lexical form before calendar parsing.
    if type(value) is not str or UTC_TIMESTAMP_PATTERN.fullmatch(value) is None:
        # Reject offsets and fractional seconds so append ordering stays portable.
        raise ValidationError(f"{field} is invalid", {"field": field})
    # Parse the complete calendar/time fields to reject impossible dates.
    try:
        # Use the fixed formatter paired with the canonical writer.
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    # Convert invalid calendar fields to one stable result.
    except ValueError:
        # Do not reflect the supplied timestamp.
        raise ValidationError(f"{field} is invalid", {"field": field}) from None
    # Return the exact canonical timestamp.
    return value


# Validate one canonical UTC day already stored in an event.
def _stored_day(value, *, field: str) -> str:
    # Require the fixed lexical day form.
    if type(value) is not str or UTC_DAY_PATTERN.fullmatch(value) is None:
        # Reject ambiguous or padded dates.
        raise ValidationError(f"{field} is invalid", {"field": field})
    # Parse the complete calendar fields to reject impossible days.
    try:
        # Use the exact year-month-day formatter.
        datetime.strptime(value, "%Y-%m-%d")
    # Convert invalid calendar fields to one stable result.
    except ValueError:
        # Do not reflect the supplied day.
        raise ValidationError(f"{field} is invalid", {"field": field}) from None
    # Return the exact canonical day.
    return value


# Hash one canonical semantic envelope for exact replay/conflict decisions.
def _fingerprint(value: Mapping[str, Any]) -> str:
    # Encode only the reviewed internal semantics before hashing.
    encoded = _canonical_json(value, field="request_semantics").encode("utf-8")
    # Return a portable lower-case SHA-256 digest.
    return hashlib.sha256(encoded).hexdigest()


# Canonicalize optional server-selected bot strategy identifiers and versions.
def _bot_strategy(value) -> str:
    # Treat no bot opponent as one explicit empty mapping.
    candidate = {} if value is None else value
    # Require named strategy slots rather than an ordered or scalar payload.
    if not isinstance(candidate, Mapping):
        # Reject malformed internal strategy metadata before attempt admission.
        raise ValidationError("bot_strategy must be an object")
    # Copy once so later caller mutation cannot change fingerprint semantics.
    normalized = dict(candidate)
    # Require bounded non-empty strings for each strategy id/version pair.
    if any(type(key) is not str or not key or len(key) > 64 or type(item) is not str or not item or len(item) > 128 for key, item in normalized.items()):
        # Never reflect strategy metadata in the stable error.
        raise ValidationError("bot_strategy is invalid")
    # Return the exact canonical metadata representation.
    return _canonical_json(normalized, field="bot_strategy")


# Describe one deterministic, versioned internal scoring result.
@dataclass(frozen=True)
class ChallengeScore:
    # Store only the bounded integer derived by trusted game rules.
    points: int
    # Store the disclosed formula inputs as a JSON-compatible mapping.
    formula_inputs: Mapping[str, Any]

    # Validate the game-supplied result before it can become a ranked event.
    def __post_init__(self) -> None:
        # Reject booleans and non-integers even though Python treats bool as int.
        if type(self.points) is not int or not MIN_POINTS <= self.points <= MAX_POINTS:
            # Fail closed on a malformed or out-of-range formula result.
            raise ValidationError("Challenge score must be an integer from 0 through 1000")
        # Require a mapping so disclosed formula inputs retain named meaning.
        if not isinstance(self.formula_inputs, Mapping):
            # Reject scalar or sequence inputs before canonicalization.
            raise ValidationError("Challenge formula inputs must be an object")
        # Prove the formula inputs have one strict portable representation.
        _canonical_json(dict(self.formula_inputs), field="formula_inputs")


# Bind one trusted game/configuration version to its server-owned score formula.
@dataclass(frozen=True)
class ChallengeRule:
    # Name the isolated game module that owns the formula.
    game_id: str
    # Version the complete scoring and validation rules.
    rules_version: str
    # Name the server-selected difficulty or configuration.
    configuration_id: str
    # Accept canonical facts and return one trusted leaf-certified versioned score result.
    score: Callable[[Mapping[str, Any]], ChallengeScore]

    # Reject malformed trusted registration before a run can start.
    def __post_init__(self) -> None:
        # Require a stable module identity.
        _identity(self.game_id, field="game_id", pattern=IDENTITY_PATTERN)
        # Require a dotted numeric rule identity.
        _identity(self.rules_version, field="rules_version", pattern=RULES_VERSION_PATTERN)
        # Require a bounded stable configuration identity.
        _identity(self.configuration_id, field="configuration_id", pattern=IDENTITY_PATTERN)
        # Reject a non-callable formula before it can be registered internally.
        if not callable(self.score):
            # Keep the diagnostic independent of the supplied object.
            raise ValidationError("Challenge score formula is invalid")


# Represent one provider-neutral append-only start or terminal event.
@dataclass(frozen=True)
class ChallengeEvent:
    # Identify the exact event independently from the run.
    event_id: str
    # Bind the event to the authenticated server-selected player.
    player_id: str
    # Bind the event to one isolated game namespace.
    game_id: str
    # Bind start and completion to one server-created run.
    run_id: str
    # Record the canonical UTC event instant.
    occurred_at: str
    # Charge and score the run against its start-day boundary.
    utc_day: str
    # Retain the coordinator-owned season identity without defining its calendar.
    season_id: str
    # Distinguish practice from ranked behavior.
    mode: str
    # Retain the exact trusted scoring revision.
    rules_version: str
    # Retain the exact trusted server configuration.
    configuration_id: str
    # Retain only the commitment identity, never active secret material.
    commitment_id: str
    # Retain canonical bot strategy identifiers/versions with no private state.
    bot_strategy_json: str
    # Record the one-based ranked attempt or zero for practice.
    attempt_ordinal: int
    # Distinguish start from terminal events.
    kind: str
    # Publish only active, completed, or rejected lifecycle meaning.
    status: str
    # Retain canonical raw facts only on terminal events.
    performance_facts_json: str
    # Retain canonical disclosed formula inputs only on accepted terminals.
    formula_inputs_json: str
    # Retain the bounded deterministic ranked score.
    awarded_points: int
    # Retain only the positive change to the counted daily best.
    counted_best_delta: int
    # Retain the terminal replay/action proof without active secret material.
    action_digest: str
    # Bind exact retries to one caller-stable operation key.
    idempotency_key: str
    # Bind key reuse to its complete canonical semantics.
    request_fingerprint: str
    # Retain accepted/rejected terminal validation or an empty start marker.
    validation_outcome: str

    # Validate every future provider-decoded event before state projection.
    def __post_init__(self) -> None:
        # Validate every server-owned identity independently.
        _identity(self.event_id, field="event_id")
        _identity(self.player_id, field="player_id")
        _identity(self.game_id, field="game_id", pattern=IDENTITY_PATTERN)
        _identity(self.run_id, field="run_id")
        # Require one exact canonical event timestamp and start-day owner.
        _stored_utc(self.occurred_at, field="occurred_at")
        _stored_day(self.utc_day, field="utc_day")
        # Require a stable server-owned season identity without interpreting it here.
        _identity(self.season_id, field="season_id")
        # This foundation deliberately has no durable practice-event shape.
        if self.mode != "ranked":
            # Refuse any adapter attempt to persist practice points or attempts.
            raise ValidationError("Challenge journal mode must be ranked")
        # Validate immutable rule and configuration identities.
        _identity(self.rules_version, field="rules_version", pattern=RULES_VERSION_PATTERN)
        _identity(self.configuration_id, field="configuration_id", pattern=IDENTITY_PATTERN)
        # Require one safe commitment reference and canonical non-secret bot metadata.
        _identity(self.commitment_id, field="commitment_id")
        _canonical_mapping_json(self.bot_strategy_json, field="bot_strategy_json")
        # Require an exact one-based product-approved attempt ordinal.
        if type(self.attempt_ordinal) is not int or not 1 <= self.attempt_ordinal <= RANKED_ATTEMPTS_PER_UTC_DAY:
            # Reject zero, booleans, gaps beyond the daily limit, and scalars.
            raise ValidationError("Challenge attempt ordinal is invalid")
        # Require one known append-only event kind.
        if self.kind not in EVENT_KINDS:
            # Reject unknown lifecycle events rather than ignoring them.
            raise ValidationError("Challenge event kind is invalid")
        # Validate the stable operation key and its complete semantic fingerprint.
        _idempotency_key(self.idempotency_key)
        _identity(self.request_fingerprint, field="request_fingerprint", pattern=DIGEST_PATTERN)
        # Reject booleans, fractions, and out-of-range persisted scores.
        if type(self.awarded_points) is not int or not MIN_POINTS <= self.awarded_points <= MAX_POINTS:
            # Keep persisted score validation identical to formula validation.
            raise ValidationError("Challenge event points are invalid")
        # Require a nonnegative integer best delta no larger than the event score.
        if type(self.counted_best_delta) is not int or not 0 <= self.counted_best_delta <= self.awarded_points:
            # Reject additive, negative, or malformed deltas before projection.
            raise ValidationError("Challenge event best delta is invalid")
        # Validate the exact empty-audit shape of a start event.
        if self.kind == "started":
            # Require starts to remain active with no outcome-derived data.
            if (self.status, self.performance_facts_json, self.formula_inputs_json, self.awarded_points, self.counted_best_delta, self.action_digest, self.validation_outcome) != ("active", "", "", 0, 0, "", ""):
                # Reject any score, terminal evidence, or terminal state on admission.
                raise ValidationError("Challenge start event is invalid")
            # Bind every decoded start to the calendar day derived from its canonical instant.
            if self.utc_day != _utc_day(self.occurred_at):
                # Reject a provider row that could charge the attempt to another day.
                raise ValidationError("Challenge start UTC day is inconsistent")
            # Stop after the complete start-shape proof.
            return
        # Require one closed terminal validation outcome.
        if self.validation_outcome not in VALIDATION_OUTCOMES:
            # Reject an ambiguous terminal decision.
            raise ValidationError("Challenge terminal validation outcome is invalid")
        # Require terminal action/replay evidence.
        _identity(self.action_digest, field="action_digest", pattern=DIGEST_PATTERN)
        # Require canonical raw performance facts on every terminal.
        _canonical_mapping_json(self.performance_facts_json, field="performance_facts_json")
        # Accepted terminal events own the deterministic completed shape.
        if self.validation_outcome == ACCEPTED:
            # Require completed status plus canonical disclosed formula inputs.
            if self.status != "completed":
                # Reject disagreement between status and validation outcome.
                raise ValidationError("Challenge accepted terminal status is invalid")
            # Validate formula-input audit bytes even when the mapping is empty.
            _canonical_mapping_json(self.formula_inputs_json, field="formula_inputs_json")
            # Stop after accepted-terminal validation.
            return
        # Rejected terminals must never carry points, deltas, or formula inputs.
        if (self.status, self.formula_inputs_json, self.awarded_points, self.counted_best_delta) != ("rejected", "", 0, 0):
            # Refuse any persisted score derived from a rejected run.
            raise ValidationError("Challenge rejected terminal event is invalid")

    # Project one explicit storage candidate without leaking dataclass internals.
    def to_record(self) -> dict:
        # Return only the reviewed provider-neutral field inventory.
        return {field: getattr(self, field) for field in EVENT_FIELDS}


# Publish a bounded response derived from one immutable event or practice run.
@dataclass(frozen=True)
class ChallengeReceipt:
    # Identify the event that committed the result, or no event for practice.
    event_id: str | None
    # Identify the server-created run.
    run_id: str
    # Identify the game and policy version used.
    game_id: str
    # Distinguish practice from ranked response meaning.
    mode: str
    # Retain the immutable scoring revision.
    rules_version: str
    # Retain the immutable server configuration.
    configuration_id: str
    # Retain the server-owned season identity without exposing calendar policy.
    season_id: str
    # Retain the non-secret seed/config commitment identity.
    commitment_id: str
    # Retain the ranked start day.
    utc_day: str
    # Retain the one-based ranked attempt or zero for practice.
    attempt_ordinal: int
    # Publish active, completed, or rejected status.
    status: str
    # Publish the deterministic score without wallet semantics.
    awarded_points: int
    # Publish only the change to the counted daily best.
    counted_best_delta: int
    # State whether this policy class requires durable journal ownership.
    durable: bool
    # State the closed-vocabulary validation result when terminal.
    validation_outcome: str


# Return one receipt plus zero or one append candidate.
@dataclass(frozen=True)
class ChallengeTransition:
    # Carry only newly owned events; exact retries and practice carry none.
    events: tuple[ChallengeEvent, ...]
    # Carry the stable player-visible operation result.
    receipt: ChallengeReceipt


# Summarize ranked attempt and best-score state for one game/day.
@dataclass(frozen=True)
class ChallengeDayState:
    # Count every valid start, including abandoned or rejected runs.
    attempts_started: int
    # Publish the bounded remaining allowance.
    attempts_remaining: int
    # Publish the highest accepted deterministic score.
    daily_best: int
    # Identify the first run that established the current best.
    counted_run_id: str | None


# Validate that every supplied event belongs to one player and game.
def _validated_events(events: Iterable[ChallengeEvent], *, player_id: str, game_id: str) -> tuple[ChallengeEvent, ...]:
    # Materialize once so generators cannot change between validation passes.
    rows = tuple(events)
    # Reject non-events rather than trusting provider-shaped dictionaries in the kernel.
    if any(not isinstance(event, ChallengeEvent) for event in rows):
        # Preserve the adapter boundary: adapters must validate/decode records first.
        raise ValidationError("Challenge journal contains an invalid event")
    # Reject cross-subject or cross-game over-return from a future adapter.
    if any(event.player_id != player_id or event.game_id != game_id for event in rows):
        # Fail closed so another subject or namespace can never satisfy state.
        raise ValidationError("Challenge journal scope is invalid")
    # Require unique event identities across the scoped journal.
    if len({event.event_id for event in rows}) != len(rows):
        # Reject duplicate physical events before computing any projection.
        raise ConflictError("Challenge journal event identity is duplicated")
    # Require one immutable meaning for every operation key in the complete scope.
    if len({event.idempotency_key for event in rows}) != len(rows):
        # Refuse ambiguous replay authority even when the duplicate rows are otherwise valid.
        raise ConflictError("Challenge journal idempotency key is duplicated")
    # Index every charged start and its append position before validating terminal joins.
    starts = {}
    start_positions = {}
    for position, event in enumerate(rows):
        # Terminal rows are validated after the complete start index exists.
        if event.kind != "started":
            continue
        # One server-created run identity can consume only one ranked attempt globally.
        if event.run_id in starts:
            raise ConflictError("Challenge ranked run identity is duplicated")
        # Retain the immutable start authority and ordering evidence.
        starts[event.run_id] = event
        start_positions[event.run_id] = position
    # Name every field a terminal must inherit exactly from its charged start.
    authority_fields = (
        "utc_day",
        "attempt_ordinal",
        "rules_version",
        "configuration_id",
        "season_id",
        "commitment_id",
        "bot_strategy_json",
    )
    # Track terminal ownership across the complete journal, not only one projected day.
    terminal_runs = set()
    for position, event in enumerate(rows):
        # Start rows have already established their immutable authority.
        if event.kind != "completed":
            continue
        # Reject an uncharged completion without disclosing any other subject.
        start = starts.get(event.run_id)
        if start is None:
            raise ConflictError("Challenge terminal event has no ranked start")
        # Reject a second terminal even when it is stored under another UTC day.
        if event.run_id in terminal_runs:
            raise ConflictError("Challenge run has multiple terminal events")
        # Require append order to preserve the charged-start-before-result lifecycle.
        if position < start_positions[event.run_id]:
            raise ConflictError("Challenge terminal event precedes its ranked start")
        # Require the canonical server completion instant not to precede admission.
        if event.occurred_at < start.occurred_at:
            raise ConflictError("Challenge terminal time precedes its ranked start")
        # Refuse any decoded terminal that rewrites immutable start authority.
        if any(getattr(event, field) != getattr(start, field) for field in authority_fields):
            raise ConflictError("Challenge terminal authority is inconsistent")
        # Record the one accepted terminal owner only after every join check passes.
        terminal_runs.add(event.run_id)
    # Return the validated immutable journal view.
    return rows


# Select one UTC day after validating the complete player/game idempotency scope.
def _scoped_events(events: Iterable[ChallengeEvent], *, player_id: str, game_id: str, utc_day: str) -> tuple[ChallengeEvent, ...]:
    # Validate the wider player/game journal before filtering its day projection.
    rows = _validated_events(events, player_id=player_id, game_id=game_id)
    # Return only events charged to the requested UTC day.
    return tuple(event for event in rows if event.utc_day == utc_day)


# Validate one ranked journal and return its deterministic day projection.
def project_day(events: Iterable[ChallengeEvent], *, player_id: str, game_id: str, utc_day: str) -> ChallengeDayState:
    # Validate exact identities used to scope future provider reads.
    player_id = _identity(player_id, field="player_id")
    game_id = _identity(game_id, field="game_id", pattern=IDENTITY_PATTERN)
    utc_day = _identity(utc_day, field="utc_day")
    # Read only the requested player/game/day journal.
    rows = _scoped_events(events, player_id=player_id, game_id=game_id, utc_day=utc_day)
    # Select ranked starts in append order.
    starts = [event for event in rows if event.kind == "started" and event.mode == "ranked"]
    # Require the one-based attempt ordinal to be contiguous and append ordered.
    if [event.attempt_ordinal for event in starts] != list(range(1, len(starts) + 1)):
        # Reject gaps, duplicates, or reordered starts before granting another attempt.
        raise ConflictError("Challenge ranked attempt journal is not contiguous")
    # Reject a journal that already exceeds the product-approved allowance.
    if len(starts) > RANKED_ATTEMPTS_PER_UTC_DAY:
        # Fail closed instead of normalizing away an over-admission defect.
        raise ConflictError("Challenge ranked attempt journal exceeds the daily limit")
    # Index each valid start by its server-created run identity.
    start_by_run = {event.run_id: event for event in starts}
    # Select every terminal ranked event.
    terminals = [event for event in rows if event.kind == "completed" and event.mode == "ranked"]
    # Require every terminal event to reference one start in the same scoped day.
    if any(event.run_id not in start_by_run for event in terminals):
        # Reject orphaned completions rather than awarding uncharged scores.
        raise ConflictError("Challenge terminal event has no ranked start")
    # Require at most one terminal event per run.
    if len({event.run_id for event in terminals}) != len(terminals):
        # Reject a second terminal result even when a future adapter over-appends.
        raise ConflictError("Challenge run has multiple terminal events")
    # Index journal position so completion can never precede its charged start.
    position_by_event = {event.event_id: index for index, event in enumerate(rows)}
    # Require every terminal append to follow its start append.
    if any(position_by_event[event.event_id] < position_by_event[start_by_run[event.run_id].event_id] for event in terminals):
        # Reject reordered history before any best-score projection.
        raise ConflictError("Challenge terminal event precedes its ranked start")
    # Track the highest accepted score without summing points like a wallet.
    daily_best = 0
    # Track the first run that established the current deterministic best.
    counted_run_id = None
    # Fold terminal events in append order.
    for event in terminals:
        # Exclude rejected validation outcomes from counted points.
        if event.validation_outcome != ACCEPTED:
            # Preserve the prior best across a rejected run.
            continue
        # Derive the only valid counted-best delta for this append position.
        expected_delta = max(0, event.awarded_points - daily_best)
        # Reject stored aggregate evidence that disagrees with raw score history.
        if event.counted_best_delta != expected_delta:
            # Fail closed rather than trusting a provider-authored aggregate.
            raise ConflictError("Challenge counted-best delta is inconsistent")
        # Advance only when the accepted score is strictly higher.
        if event.awarded_points > daily_best:
            # Adopt the new server-derived best.
            daily_best = event.awarded_points
            # Retain the run that established it.
            counted_run_id = event.run_id
    # Publish attempts, remaining allowance, and best-score state.
    return ChallengeDayState(
        attempts_started=len(starts),
        attempts_remaining=RANKED_ATTEMPTS_PER_UTC_DAY - len(starts),
        daily_best=daily_best,
        counted_run_id=counted_run_id,
    )


# Reconstruct the exact bounded receipt from one immutable event.
def _receipt(event: ChallengeEvent) -> ChallengeReceipt:
    # Preserve the committed event values without recomputing mutable state.
    return ChallengeReceipt(
        event_id=event.event_id,
        run_id=event.run_id,
        game_id=event.game_id,
        mode=event.mode,
        rules_version=event.rules_version,
        configuration_id=event.configuration_id,
        season_id=event.season_id,
        commitment_id=event.commitment_id,
        utc_day=event.utc_day,
        attempt_ordinal=event.attempt_ordinal,
        status=event.status,
        awarded_points=event.awarded_points,
        counted_best_delta=event.counted_best_delta,
        durable=True,
        validation_outcome=event.validation_outcome,
    )


# Resolve an exact retry or reject changed-meaning key reuse.
def _replay(rows: tuple[ChallengeEvent, ...], *, idempotency_key: str, request_fingerprint: str) -> ChallengeTransition | None:
    # Select only an event previously committed under the operation key.
    prior = next((event for event in rows if event.idempotency_key == idempotency_key), None)
    # Report no replay when the key has not committed in this scope.
    if prior is None:
        # Allow the caller to construct one new append candidate.
        return None
    # Reject the same key when any semantic field changed.
    if prior.request_fingerprint != request_fingerprint:
        # Preserve the already committed result without another append.
        raise ConflictError("Challenge idempotency key was reused with different semantics")
    # Return the exact committed receipt with no new event.
    return ChallengeTransition(events=(), receipt=_receipt(prior))


# Start one ranked run and consume its day allowance before play begins. (CHALLENGE-002)
def start_ranked(
    events: Iterable[ChallengeEvent],
    *,
    rule: ChallengeRule,
    player_id: str,
    started_at: datetime,
    idempotency_key: str,
    season_id: str,
    commitment_id: str,
    bot_strategy: Mapping[str, str] | None,
    new_run_id: Callable[[], str],
    new_event_id: Callable[[], str],
) -> ChallengeTransition:
    # Validate the authenticated internal subject identity.
    player_id = _identity(player_id, field="player_id")
    # Validate the operation key before reading replay state.
    idempotency_key = _idempotency_key(idempotency_key)
    # Validate the server-selected season without inventing calendar semantics.
    season_id = _identity(season_id, field="season_id")
    # Validate the non-secret seed/config commitment reference.
    commitment_id = _identity(commitment_id, field="commitment_id")
    # Canonicalize optional bot strategy ids/versions without private decisions.
    bot_strategy_json = _bot_strategy(bot_strategy)
    # Canonicalize the server clock once for day ownership and semantics.
    occurred_at = _utc(started_at, field="started_at")
    # Charge the run to the UTC day on which gameplay begins.
    utc_day = _utc_day(occurred_at)
    # Validate the complete player/game journal before retry or allowance decisions.
    all_rows = _validated_events(events, player_id=player_id, game_id=rule.game_id)
    # Select only current-day rows for attempt and best-score projection.
    rows = tuple(event for event in all_rows if event.utc_day == utc_day)
    # Bind retry semantics only to client-stable and policy-stable fields.
    request_fingerprint = _fingerprint(
        {
            "operation": "ranked_start",
            "player_id": player_id,
            "game_id": rule.game_id,
            "rules_version": rule.rules_version,
            "configuration_id": rule.configuration_id,
            "utc_day": utc_day,
            "season_id": season_id,
            "commitment_id": commitment_id,
            "bot_strategy": json.loads(bot_strategy_json),
        }
    )
    # Return a compatible winner before generating any new identity.
    replay = _replay(all_rows, idempotency_key=idempotency_key, request_fingerprint=request_fingerprint)
    # Stop after the exact committed replay.
    if replay is not None:
        # Preserve the original event and attempt ordinal.
        return replay
    # Project the complete daily allowance and accepted best state.
    state = project_day(rows, player_id=player_id, game_id=rule.game_id, utc_day=utc_day)
    # Reject a fourth start even when earlier runs were abandoned or rejected.
    if state.attempts_remaining == 0:
        # Expose only the stable product limit.
        raise ConflictError("Challenge ranked attempt limit reached", {"limit": RANKED_ATTEMPTS_PER_UTC_DAY})
    # Generate a run identity only after replay and allowance validation.
    run_id = _identity(new_run_id(), field="run_id")
    # Prevent a broken generator from colliding with a prior run.
    if any(event.run_id == run_id for event in all_rows):
        # Fail without appending under the duplicate server identity.
        raise ConflictError("Challenge run identity is duplicated")
    # Generate one append identity only for the new admitted transition.
    event_id = _identity(new_event_id(), field="event_id")
    # Prevent a broken generator from colliding with a prior event.
    if any(event.event_id == event_id for event in all_rows):
        # Fail without appending under the duplicate event identity.
        raise ConflictError("Challenge event identity is duplicated")
    # Construct the complete ranked-start append candidate.
    event = ChallengeEvent(
        event_id=event_id,
        player_id=player_id,
        game_id=rule.game_id,
        run_id=run_id,
        occurred_at=occurred_at,
        utc_day=utc_day,
        season_id=season_id,
        mode="ranked",
        rules_version=rule.rules_version,
        configuration_id=rule.configuration_id,
        commitment_id=commitment_id,
        bot_strategy_json=bot_strategy_json,
        attempt_ordinal=state.attempts_started + 1,
        kind="started",
        status="active",
        performance_facts_json="",
        formula_inputs_json="",
        awarded_points=0,
        counted_best_delta=0,
        action_digest="",
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        validation_outcome="",
    )
    # Return one append candidate for the future atomic adapter.
    return ChallengeTransition(events=(event,), receipt=_receipt(event))


# Start unlimited practice without creating a point-journal candidate. (CHALLENGE-001)
def start_practice(*, rule: ChallengeRule, player_id: str, started_at: datetime, new_run_id: Callable[[], str]) -> ChallengeTransition:
    # Validate the authenticated internal subject even though practice is non-durable.
    _identity(player_id, field="player_id")
    # Canonicalize the server start clock for a stable ephemeral receipt.
    occurred_at = _utc(started_at, field="started_at")
    # Generate one non-durable run identity for subsequent practice completion.
    run_id = _identity(new_run_id(), field="run_id")
    # Publish an explicit non-persisted active receipt and no append candidate.
    receipt = ChallengeReceipt(
        event_id=None,
        run_id=run_id,
        game_id=rule.game_id,
        mode="practice",
        rules_version=rule.rules_version,
        configuration_id=rule.configuration_id,
        season_id="",
        commitment_id="",
        utc_day=_utc_day(occurred_at),
        attempt_ordinal=0,
        status="active",
        awarded_points=0,
        counted_best_delta=0,
        durable=False,
        validation_outcome="",
    )
    # Return no journal event so practice can never change durable Challenge Points.
    return ChallengeTransition(events=(), receipt=receipt)


# Execute one trusted score formula and validate its bounded canonical return shape.
def _score(rule: ChallengeRule, performance_facts: Mapping[str, Any]) -> tuple[ChallengeScore, str, str]:
    # Require named facts so clients cannot submit a scalar outcome surrogate.
    if not isinstance(performance_facts, Mapping):
        # Reject before the trusted rule function executes.
        raise ValidationError("performance_facts must be an object")
    # Copy once so a mutable caller mapping cannot change during scoring.
    facts = dict(performance_facts)
    # Canonicalize the complete server-owned facts before rule execution.
    performance_facts_json = _canonical_json(facts, field="performance_facts")
    # Execute only the rule registered by trusted server code.
    result = rule.score(facts)
    # Reject formulas that bypass the explicit bounded result type.
    if not isinstance(result, ChallengeScore):
        # Keep malformed game-rule diagnostics fixed and private.
        raise ValidationError("Challenge score formula returned an invalid result")
    # Canonicalize disclosed formula inputs for deterministic audit comparison.
    formula_inputs_json = _canonical_json(dict(result.formula_inputs), field="formula_inputs")
    # Return the validated score plus both canonical audit representations.
    return result, performance_facts_json, formula_inputs_json


# Complete one ranked run with server-derived score and daily-best delta. (CHALLENGE-002)
def complete_ranked(
    events: Iterable[ChallengeEvent],
    *,
    rule: ChallengeRule,
    player_id: str,
    run_id: str,
    completed_at: datetime,
    idempotency_key: str,
    performance_facts: Mapping[str, Any],
    action_digest: str,
    validation_outcome: str,
    new_event_id: Callable[[], str],
) -> ChallengeTransition:
    # Validate the authenticated internal subject and server-created run identities.
    player_id = _identity(player_id, field="player_id")
    run_id = _identity(run_id, field="run_id")
    # Validate the caller-stable terminal operation key.
    idempotency_key = _idempotency_key(idempotency_key)
    # Canonicalize the completion clock before formula or identity generation.
    occurred_at = _utc(completed_at, field="completed_at")
    # Require one closed validation outcome before invoking any formula.
    if validation_outcome not in VALIDATION_OUTCOMES:
        # Reject ambiguous truthy states rather than treating them as accepted.
        raise ValidationError("validation_outcome is invalid")
    # Require one complete replay/action digest for terminal audit.
    action_digest = _identity(action_digest, field="action_digest", pattern=DIGEST_PATTERN)
    # Canonicalize terminal facts before any fingerprint or score decision.
    if not isinstance(performance_facts, Mapping):
        # Reject scalar caller-authored scores or outcomes.
        raise ValidationError("performance_facts must be an object")
    # Copy the trusted canonical facts exactly once.
    facts = dict(performance_facts)
    # Prove the facts have a strict provider-independent representation.
    facts_json = _canonical_json(facts, field="performance_facts")
    # Locate the ranked start without trusting a caller-supplied day.
    all_rows = _validated_events(events, player_id=player_id, game_id=rule.game_id)
    # Select only this authenticated subject/game/run start.
    start = next((event for event in all_rows if isinstance(event, ChallengeEvent) and event.player_id == player_id and event.game_id == rule.game_id and event.run_id == run_id and event.kind == "started" and event.mode == "ranked"), None)
    # Reject completion without a charged ranked attempt.
    if start is None:
        # Do not reveal another subject's run existence.
        raise ConflictError("Challenge ranked run is not active")
    # Require completion under the exact immutable start policy.
    if start.rules_version != rule.rules_version or start.configuration_id != rule.configuration_id:
        # Reject changed rules/configuration rather than silently rescoring.
        raise ConflictError("Challenge run policy changed before completion")
    # Reject a terminal clock that precedes the server-owned start instant.
    if occurred_at < start.occurred_at:
        # Preserve append order and elapsed-time authority without accepting client clocks.
        raise ConflictError("Challenge completion precedes its ranked start")
    # Scope and validate the complete start-day journal.
    rows = _scoped_events(all_rows, player_id=player_id, game_id=rule.game_id, utc_day=start.utc_day)
    # Bind every terminal semantic input before score calculation or identity generation.
    request_fingerprint = _fingerprint(
        {
            "operation": "ranked_complete",
            "player_id": player_id,
            "game_id": rule.game_id,
            "run_id": run_id,
            "rules_version": rule.rules_version,
            "configuration_id": rule.configuration_id,
            "season_id": start.season_id,
            "commitment_id": start.commitment_id,
            "bot_strategy": json.loads(start.bot_strategy_json),
            "performance_facts": facts,
            "action_digest": action_digest,
            "validation_outcome": validation_outcome,
        }
    )
    # Return an exact committed retry before invoking the formula again.
    replay = _replay(all_rows, idempotency_key=idempotency_key, request_fingerprint=request_fingerprint)
    # Stop after the compatible replay.
    if replay is not None:
        # Preserve exact prior receipt bytes and no append candidate.
        return replay
    # Reject a second terminal operation under another key.
    if any(event.run_id == run_id and event.kind == "completed" for event in all_rows):
        # Preserve the first terminal result as the only authority.
        raise ConflictError("Challenge ranked run is already terminal")
    # Project the accepted best before this result.
    state = project_day(rows, player_id=player_id, game_id=rule.game_id, utc_day=start.utc_day)
    # Default rejected validation to no score and no formula-input audit.
    score = ChallengeScore(points=0, formula_inputs={})
    # Reuse the already canonical rejected facts representation.
    performance_facts_json = facts_json
    # Store no scoring inputs for a run the server refused to score.
    formula_inputs_json = ""
    # Execute the trusted versioned rule only for a server-accepted replay/state.
    if validation_outcome == ACCEPTED:
        # Derive points and disclosed inputs from trusted canonical facts.
        score, performance_facts_json, formula_inputs_json = _score(rule, facts)
    # Count only the positive improvement over the prior accepted daily best.
    counted_best_delta = max(0, score.points - state.daily_best) if validation_outcome == ACCEPTED else 0
    # Generate one terminal append identity after all conflicts and scoring pass.
    event_id = _identity(new_event_id(), field="event_id")
    # Prevent a broken generator from colliding with a prior event.
    if any(event.event_id == event_id for event in all_rows):
        # Fail before returning an ambiguous append candidate.
        raise ConflictError("Challenge event identity is duplicated")
    # Construct the exact terminal append candidate.
    event = ChallengeEvent(
        event_id=event_id,
        player_id=player_id,
        game_id=rule.game_id,
        run_id=run_id,
        occurred_at=occurred_at,
        utc_day=start.utc_day,
        season_id=start.season_id,
        mode="ranked",
        rules_version=rule.rules_version,
        configuration_id=rule.configuration_id,
        commitment_id=start.commitment_id,
        bot_strategy_json=start.bot_strategy_json,
        attempt_ordinal=start.attempt_ordinal,
        kind="completed",
        status="completed" if validation_outcome == ACCEPTED else "rejected",
        performance_facts_json=performance_facts_json,
        formula_inputs_json=formula_inputs_json,
        awarded_points=score.points if validation_outcome == ACCEPTED else 0,
        counted_best_delta=counted_best_delta,
        action_digest=action_digest,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        validation_outcome=validation_outcome,
    )
    # Return one append candidate for the future atomic adapter.
    return ChallengeTransition(events=(event,), receipt=_receipt(event))


# Complete practice without appending or changing ranked best state. (CHALLENGE-001)
def complete_practice(
    *,
    rule: ChallengeRule,
    player_id: str,
    run_id: str,
    started_at: datetime,
    performance_facts: Mapping[str, Any],
    validation_outcome: str,
) -> ChallengeTransition:
    # Validate internal subject and ephemeral run identities.
    _identity(player_id, field="player_id")
    run_id = _identity(run_id, field="run_id")
    # Require the same closed validation outcome as ranked completion.
    if validation_outcome not in VALIDATION_OUTCOMES:
        # Refuse an ambiguous practice result.
        raise ValidationError("validation_outcome is invalid")
    # Default rejected practice to zero display points.
    awarded_points = 0
    # Run the trusted versioned formula only after server acceptance.
    if validation_outcome == ACCEPTED:
        # Derive a bounded score for non-durable player feedback.
        score, _facts_json, _formula_inputs_json = _score(rule, performance_facts)
        # Publish the derived value without creating a journal event.
        awarded_points = score.points
    # Canonicalize the original start clock for stable receipt ownership.
    occurred_at = _utc(started_at, field="started_at")
    # Build the explicit non-persisted terminal receipt.
    receipt = ChallengeReceipt(
        event_id=None,
        run_id=run_id,
        game_id=rule.game_id,
        mode="practice",
        rules_version=rule.rules_version,
        configuration_id=rule.configuration_id,
        season_id="",
        commitment_id="",
        utc_day=_utc_day(occurred_at),
        attempt_ordinal=0,
        status="completed" if validation_outcome == ACCEPTED else "rejected",
        awarded_points=awarded_points,
        counted_best_delta=0,
        durable=False,
        validation_outcome=validation_outcome,
    )
    # Return no append candidate so practice cannot affect Challenge Points history.
    return ChallengeTransition(events=(), receipt=receipt)
