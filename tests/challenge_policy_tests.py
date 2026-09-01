# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free Challenge kernel evidence. (#1091, CHALLENGE-POLICY-001, TEST-263)"""

# Import AST parsing for a structural no-wallet/no-storage dependency proof.
import ast
# Import UTC-aware test clocks for deterministic attempt-day ownership.
from datetime import datetime, timedelta, timezone
# Import immutable replacement for hostile journal fixtures.
from dataclasses import replace
# Import SHA-256 for valid synthetic terminal action evidence.
import hashlib
# Import source inspection without importing unrelated runtime providers.
import inspect
# Import deterministic identifier counters for replay-side-effect assertions.
import itertools
# Import the standard focused test framework.
import unittest

# Import the inactive policy module and immutable values under test.
from casino.core.challenges import policy
# Import stable application failures for exact hostile-path assertions.
from casino.errors import ConflictError, ValidationError


# Build one deterministic synthetic ruleset without registering a production game.
def synthetic_rule() -> policy.ChallengeRule:
    # Derive points only from server-owned canonical performance facts.
    def score(facts):
        # Clamp the disclosed integer inputs through an intentionally simple formula.
        cleared = int(facts["cleared"])
        mistakes = int(facts["mistakes"])
        # Return the bounded deterministic score and disclosed formula inputs.
        return policy.ChallengeScore(points=max(0, min(1_000, cleared * 100 - mistakes * 25)), formula_inputs={"cleared": cleared, "mistakes": mistakes})

    # Bind the synthetic rule to a non-production test namespace.
    return policy.ChallengeRule(game_id="synthetic_challenge", rules_version="1.0.0", configuration_id="standard", score=score)


# Generate stable unique internal identities while counting calls.
class IdentityFactory:
    # Start a named counter at one for readable event fixtures.
    def __init__(self, prefix):
        # Retain the fixed prefix used by every generated value.
        self.prefix = prefix
        # Retain one monotonic counter for call-count assertions.
        self.counter = itertools.count(1)
        # Count generator invocations separately from the iterator.
        self.calls = 0

    # Return one stable identity each time the policy owns a new transition.
    def __call__(self):
        # Record the generator side effect.
        self.calls += 1
        # Publish a readable unique identity.
        return f"{self.prefix}-{next(self.counter)}"


# Verify deterministic authority, attempt accounting, retries, and wallet isolation. (CHALLENGE-001, CHALLENGE-002)
class ChallengePolicyTests(unittest.TestCase):
    # Establish one trusted rule and exact UTC start instant for each test.
    def setUp(self):
        # Use one internal synthetic rule without a catalog or route registration.
        self.rule = synthetic_rule()
        # Use one exact aware UTC clock value.
        self.now = datetime(2026, 8, 31, 12, 30, tzinfo=timezone.utc)
        # Use one authenticated server-selected subject identity.
        self.player_id = "player-challenge-owner"
        # Generate run identities independently from event identities.
        self.runs = IdentityFactory("run")
        # Generate event identities independently from run identities.
        self.events = IdentityFactory("event")

    # Append the one event returned by a new ranked transition.
    def append(self, journal, transition):
        # Require a new transition to own exactly one append candidate.
        self.assertEqual(len(transition.events), 1)
        # Return a new immutable journal tuple.
        return (*journal, transition.events[0])

    # Start one ranked run with a caller-stable operation key.
    def start(self, journal, key, at=None):
        # Delegate to the pure policy with test-owned identity factories.
        return policy.start_ranked(journal, rule=self.rule, player_id=self.player_id, started_at=at or self.now, idempotency_key=key, season_id="synthetic-season-2026", commitment_id="commitment-synthetic-001", bot_strategy=None, new_run_id=self.runs, new_event_id=self.events)

    # Complete one ranked run with accepted synthetic facts.
    def complete(self, journal, run_id, key, *, facts=None, outcome=policy.ACCEPTED):
        # Derive one valid deterministic action digest.
        digest = hashlib.sha256(f"{run_id}:{key}".encode("utf-8")).hexdigest()
        # Delegate to the pure policy without any provider or wallet fixture.
        return policy.complete_ranked(journal, rule=self.rule, player_id=self.player_id, run_id=run_id, completed_at=self.now + timedelta(minutes=5), idempotency_key=key, performance_facts=facts or {"cleared": 7, "mistakes": 2}, action_digest=digest, validation_outcome=outcome, new_event_id=self.events)

    # Require practice to remain unlimited, deterministic, and completely non-durable.
    def test_practice_never_appends_or_changes_ranked_allowance(self):
        # Start one practice run without a point-journal candidate.
        started = policy.start_practice(rule=self.rule, player_id=self.player_id, started_at=self.now, new_run_id=self.runs)
        # Complete the accepted practice run through the trusted formula.
        completed = policy.complete_practice(rule=self.rule, player_id=self.player_id, run_id=started.receipt.run_id, started_at=self.now, performance_facts={"cleared": 9, "mistakes": 0}, validation_outcome=policy.ACCEPTED)
        # Require explicit non-persistence at both lifecycle boundaries.
        self.assertEqual((started.events, completed.events, started.receipt.durable, completed.receipt.durable), ((), (), False, False))
        # Require useful deterministic practice feedback without counted-best movement.
        self.assertEqual((completed.receipt.awarded_points, completed.receipt.counted_best_delta), (900, 0))
        # Require an empty ranked journal to retain all three attempts and zero best.
        self.assertEqual(policy.project_day((), player_id=self.player_id, game_id=self.rule.game_id, utc_day="2026-08-31"), policy.ChallengeDayState(0, 3, 0, None))

    # Require every start, including a rejected or abandoned run, to consume allowance.
    def test_three_ranked_starts_are_consumed_and_fourth_fails_closed(self):
        # Build one empty append-only journal.
        journal = ()
        # Admit exactly three server-owned starts.
        for attempt in range(1, 4):
            # Start under a unique operation key.
            transition = self.start(journal, f"ranked-start-key-{attempt:02d}")
            # Require contiguous one-based ordinals.
            self.assertEqual(transition.receipt.attempt_ordinal, attempt)
            # Append the admitted event.
            journal = self.append(journal, transition)
        # Require no remaining attempt regardless of absent terminal events.
        self.assertEqual(policy.project_day(journal, player_id=self.player_id, game_id=self.rule.game_id, utc_day="2026-08-31").attempts_remaining, 0)
        # Reject the fourth start before generating another identity.
        with self.assertRaisesRegex(ConflictError, "attempt limit"):
            self.start(journal, "ranked-start-key-04")
        # Require exactly three run and event identities to have been allocated.
        self.assertEqual((self.runs.calls, self.events.calls), (3, 3))

    # Require only accepted deterministic scores to advance one daily best.
    def test_daily_best_uses_positive_delta_not_additive_points(self):
        # Start and complete the first accepted run at 650 points.
        first_start = self.start((), "ranked-start-key-01")
        journal = self.append((), first_start)
        first_done = self.complete(journal, first_start.receipt.run_id, "ranked-done-key-001", facts={"cleared": 7, "mistakes": 2})
        journal = self.append(journal, first_done)
        # Require the first result to establish the complete best.
        self.assertEqual((first_done.receipt.awarded_points, first_done.receipt.counted_best_delta), (650, 650))
        # Start and complete a lower accepted run.
        second_start = self.start(journal, "ranked-start-key-02")
        journal = self.append(journal, second_start)
        second_done = self.complete(journal, second_start.receipt.run_id, "ranked-done-key-002", facts={"cleared": 5, "mistakes": 0})
        journal = self.append(journal, second_done)
        # Require the lower score not to add or reduce points.
        self.assertEqual((second_done.receipt.awarded_points, second_done.receipt.counted_best_delta), (500, 0))
        # Start and complete a higher accepted run at 900 points.
        third_start = self.start(journal, "ranked-start-key-03")
        journal = self.append(journal, third_start)
        third_done = self.complete(journal, third_start.receipt.run_id, "ranked-done-key-003", facts={"cleared": 9, "mistakes": 0})
        journal = self.append(journal, third_done)
        # Require only the improvement over 650 to contribute.
        self.assertEqual((third_done.receipt.awarded_points, third_done.receipt.counted_best_delta), (900, 250))
        # Require the projection to select the highest accepted score, never the sum.
        state = policy.project_day(journal, player_id=self.player_id, game_id=self.rule.game_id, utc_day="2026-08-31")
        self.assertEqual((state.daily_best, state.counted_run_id), (900, third_start.receipt.run_id))

    # Require exact retries to return the committed receipt without generators or appends.
    def test_exact_start_and_completion_retries_are_side_effect_free(self):
        # Count accepted score execution independently from identity generation.
        score_calls = []
        original_score = self.rule.score

        # Delegate to the deterministic fixture only after recording canonical facts.
        def counting_score(facts):
            # Copy the bounded mapping so later caller mutation cannot affect the assertion.
            score_calls.append(dict(facts))
            # Preserve the existing synthetic formula semantics.
            return original_score(facts)

        # Keep the exact rule identity while observing score execution.
        self.rule = policy.ChallengeRule(game_id=self.rule.game_id, rules_version=self.rule.rules_version, configuration_id=self.rule.configuration_id, score=counting_score)
        # Admit one ranked start and append its event.
        first_start = self.start((), "ranked-start-retry")
        journal = self.append((), first_start)
        # Starting a run never invokes its future terminal scorer.
        self.assertEqual(score_calls, [])
        # Snapshot generator calls before retry.
        generated_after_start = (self.runs.calls, self.events.calls)
        # Retry the identical start operation.
        repeated_start = self.start(journal, "ranked-start-retry")
        # Require exact receipt replay with no new event, identity, or score execution.
        self.assertEqual((repeated_start.receipt, repeated_start.events, (self.runs.calls, self.events.calls), score_calls), (first_start.receipt, (), generated_after_start, []))
        # Complete and append the first terminal event.
        first_done = self.complete(journal, first_start.receipt.run_id, "ranked-done-retry")
        journal = self.append(journal, first_done)
        # Require the first accepted terminal to evaluate the deterministic fixture once.
        self.assertEqual(score_calls, [{"cleared": 7, "mistakes": 2}])
        # Snapshot the terminal generator call count.
        generated_after_done = self.events.calls
        # Retry the exact terminal semantics.
        repeated_done = self.complete(journal, first_start.receipt.run_id, "ranked-done-retry")
        # Require exact receipt replay and no new event, generator call, or rescoring.
        self.assertEqual((repeated_done.receipt, repeated_done.events, self.events.calls, score_calls), (first_done.receipt, (), generated_after_done, [{"cleared": 7, "mistakes": 2}]))

    # Require changed-meaning key reuse and second terminal keys to fail closed.
    def test_idempotency_conflicts_never_rescore_or_append(self):
        # Admit one start and append it.
        started = self.start((), "ranked-start-conflict")
        journal = self.append((), started)
        # Reuse the start key on another UTC day and require a semantic conflict.
        with self.assertRaisesRegex(ConflictError, "different semantics"):
            self.start(journal, "ranked-start-conflict", at=self.now + timedelta(days=1))
        # Complete the run once.
        done = self.complete(journal, started.receipt.run_id, "ranked-done-conflict")
        journal = self.append(journal, done)
        # Change terminal facts under the same key and require conflict before scoring.
        with self.assertRaisesRegex(ConflictError, "different semantics"):
            self.complete(journal, started.receipt.run_id, "ranked-done-conflict", facts={"cleared": 1, "mistakes": 0})
        # Use another key for the terminal run and require first-result authority.
        with self.assertRaisesRegex(ConflictError, "already terminal"):
            self.complete(journal, started.receipt.run_id, "ranked-done-second-key")

    # Require rejected validation to consume the attempt but never run the score formula.
    def test_rejected_validation_records_zero_without_formula_execution(self):
        # Count any formula execution through a hostile replacement rule.
        formula_calls = []

        # Define a formula that would reveal accidental execution.
        def score(_facts):
            # Record the prohibited call.
            formula_calls.append(True)
            # Return a valid result only so the outcome gate is the reason it is skipped.
            return policy.ChallengeScore(points=1_000, formula_inputs={})

        # Replace only the trusted scoring callable.
        rejecting_rule = policy.ChallengeRule(game_id=self.rule.game_id, rules_version=self.rule.rules_version, configuration_id=self.rule.configuration_id, score=score)
        # Start the ranked run under the original equivalent rule identity.
        started = self.start((), "ranked-start-rejected")
        journal = self.append((), started)
        # Complete with a server-rejected validation outcome.
        digest = hashlib.sha256(b"rejected-action").hexdigest()
        transition = policy.complete_ranked(journal, rule=rejecting_rule, player_id=self.player_id, run_id=started.receipt.run_id, completed_at=self.now, idempotency_key="ranked-done-rejected", performance_facts={"caller_score": 999999}, action_digest=digest, validation_outcome=policy.REJECTED, new_event_id=self.events)
        # Require no formula call, no points, and explicit rejection.
        self.assertEqual((formula_calls, transition.receipt.awarded_points, transition.receipt.counted_best_delta, transition.receipt.status), ([], 0, 0, "rejected"))

    # Require hostile formula outputs and facts to fail before append construction.
    def test_score_bounds_and_canonical_fact_validation_fail_closed(self):
        # Prove both inclusive product-approved integer endpoints are accepted exactly.
        for value in (0, 1_000):
            # Isolate each accepted boundary from malformed-output cases.
            with self.subTest(value=value):
                score = policy.ChallengeScore(points=value, formula_inputs={"boundary": value})
                # Preserve the exact integer and disclosed canonical input mapping.
                self.assertEqual((score.points, dict(score.formula_inputs)), (value, {"boundary": value}))
        # Enumerate every forbidden point shape.
        for value in (-1, 1_001, 1.5, True, "100"):
            # Isolate each malformed output.
            with self.subTest(value=value):
                # Require the immutable score type to reject it.
                with self.assertRaises(ValidationError):
                    policy.ChallengeScore(points=value, formula_inputs={})
        # Start one valid ranked run.
        started = self.start((), "ranked-start-invalid")
        journal = self.append((), started)
        # Reject NaN before invoking the scoring formula or generating an event.
        with self.assertRaisesRegex(ValidationError, "performance_facts"):
            self.complete(journal, started.receipt.run_id, "ranked-done-invalid", facts={"cleared": float("nan"), "mistakes": 0})

    # Require cross-subject, orphaned, duplicate, and changed-policy journals to fail closed.
    def test_journal_scope_and_run_integrity_are_strict(self):
        # Admit one valid start.
        started = self.start((), "ranked-start-integrity")
        start_event = started.events[0]
        # Reject a future provider over-returning another subject's row.
        with self.assertRaisesRegex(ValidationError, "scope"):
            policy.project_day((start_event, replace(start_event, player_id="other-player", event_id="event-other")), player_id=self.player_id, game_id=self.rule.game_id, utc_day="2026-08-31")
        # Reject duplicate physical event identity.
        with self.assertRaisesRegex(ConflictError, "duplicated"):
            policy.project_day((start_event, start_event), player_id=self.player_id, game_id=self.rule.game_id, utc_day="2026-08-31")
        # Build a changed rule version without changing the game namespace.
        changed_rule = policy.ChallengeRule(game_id=self.rule.game_id, rules_version="2.0.0", configuration_id=self.rule.configuration_id, score=self.rule.score)
        # Reject completion after a rules-version change.
        digest = hashlib.sha256(b"changed-rule").hexdigest()
        with self.assertRaisesRegex(ConflictError, "policy changed"):
            policy.complete_ranked((start_event,), rule=changed_rule, player_id=self.player_id, run_id=start_event.run_id, completed_at=self.now, idempotency_key="ranked-done-new-rules", performance_facts={"cleared": 1, "mistakes": 0}, action_digest=digest, validation_outcome=policy.ACCEPTED, new_event_id=self.events)

    # Require decoded starts to preserve one day, run, and operation identity.
    def test_decoded_start_identity_and_day_invariants_fail_closed(self):
        # Admit one canonical start as the authority for hostile decoded variants.
        started = self.start((), "ranked-start-decoded")
        start_event = started.events[0]
        # Reject a single decoded record charged to a day other than its start instant.
        with self.assertRaisesRegex(ValidationError, "UTC day"):
            replace(start_event, utc_day="2026-09-01")
        # Build a second structurally valid start that reuses the server run identity.
        duplicate_run = replace(start_event, event_id="event-duplicate-run", attempt_ordinal=2, idempotency_key="ranked-start-duplicate-run", request_fingerprint="1" * 64)
        # Reject the duplicate run before per-day projection can grant another attempt.
        with self.assertRaisesRegex(ConflictError, "run identity"):
            policy.project_day((start_event, duplicate_run), player_id=self.player_id, game_id=self.rule.game_id, utc_day="2026-08-31")
        # Build a distinct start that reuses the first operation key under new semantics.
        duplicate_key = replace(start_event, event_id="event-duplicate-key", run_id="run-duplicate-key", attempt_ordinal=2, request_fingerprint="2" * 64)
        # Reject ambiguous durable replay ownership across otherwise valid rows.
        with self.assertRaisesRegex(ConflictError, "idempotency key"):
            policy.project_day((start_event, duplicate_key), player_id=self.player_id, game_id=self.rule.game_id, utc_day="2026-08-31")
        # Snapshot identity generation before attempting a new start over corrupt history.
        generated_before = (self.runs.calls, self.events.calls)
        # Fail before allocating a run or event identity from the corrupt journal.
        with self.assertRaisesRegex(ConflictError, "run identity"):
            self.start((start_event, duplicate_run), "ranked-start-after-corruption")
        self.assertEqual((self.runs.calls, self.events.calls), generated_before)

    # Require start-day ownership to reset attempts while retaining global key conflicts.
    def test_utc_day_projection_resets_attempts_without_resetting_idempotency(self):
        # Admit one run on the first UTC day.
        first = self.start((), "ranked-start-global-key")
        journal = self.append((), first)
        # Admit a distinct run on the next UTC day from the complete player/game journal.
        second = self.start(journal, "ranked-start-next-day", at=self.now + timedelta(days=1))
        journal = self.append(journal, second)
        # Require each day to begin its own one-based allowance.
        first_day = policy.project_day(journal, player_id=self.player_id, game_id=self.rule.game_id, utc_day="2026-08-31")
        second_day = policy.project_day(journal, player_id=self.player_id, game_id=self.rule.game_id, utc_day="2026-09-01")
        self.assertEqual((first_day.attempts_started, second_day.attempts_started, second.receipt.attempt_ordinal), (1, 1, 1))
        # Reusing the first key on a new day remains a changed-meaning global conflict.
        with self.assertRaisesRegex(ConflictError, "different semantics"):
            self.start(journal, "ranked-start-global-key", at=self.now + timedelta(days=1))

    # Require terminal time and immutable event shapes to reject inconsistent records.
    def test_terminal_time_and_event_shape_fail_closed(self):
        # Admit one valid ranked start.
        started = self.start((), "ranked-start-event-shape")
        start_event = started.events[0]
        # Reject completion before the authoritative server start instant.
        digest = hashlib.sha256(b"early-completion").hexdigest()
        with self.assertRaisesRegex(ConflictError, "precedes"):
            policy.complete_ranked((start_event,), rule=self.rule, player_id=self.player_id, run_id=start_event.run_id, completed_at=self.now - timedelta(seconds=1), idempotency_key="ranked-done-too-early", performance_facts={"cleared": 1, "mistakes": 0}, action_digest=digest, validation_outcome=policy.ACCEPTED, new_event_id=self.events)
        # Reject any adapter-decoded start that carries score data.
        with self.assertRaisesRegex(ValidationError, "start event"):
            replace(start_event, awarded_points=1, counted_best_delta=1)
        # Reject a durable practice event categorically.
        with self.assertRaisesRegex(ValidationError, "mode must be ranked"):
            replace(start_event, mode="practice")
        # Complete one valid accepted run for history-order and delta checks.
        completed = self.complete((start_event,), start_event.run_id, "ranked-done-event-shape")
        terminal_event = completed.events[0]
        # Reject a journal whose terminal append precedes its charged start.
        with self.assertRaisesRegex(ConflictError, "precedes"):
            policy.project_day((terminal_event, start_event), player_id=self.player_id, game_id=self.rule.game_id, utc_day="2026-08-31")
        # Build a structurally valid but historically inconsistent best delta.
        inconsistent_delta = replace(terminal_event, counted_best_delta=1)
        # Reject provider aggregate evidence that disagrees with raw event history.
        with self.assertRaisesRegex(ConflictError, "delta is inconsistent"):
            policy.project_day((start_event, inconsistent_delta), player_id=self.player_id, game_id=self.rule.game_id, utc_day="2026-08-31")

    # Require every decoded terminal to inherit the exact charged-start authority.
    def test_decoded_terminal_must_match_start_authority(self):
        # Build one valid start and accepted terminal as the immutable join baseline.
        started = self.start((), "ranked-start-terminal-authority")
        start_event = started.events[0]
        completed = self.complete((start_event,), start_event.run_id, "ranked-done-terminal-authority")
        terminal_event = completed.events[0]
        # Enumerate every individually valid terminal field that cannot drift from its start.
        changed_authority = (
            ("utc_day", "2026-09-01"),
            ("attempt_ordinal", 2),
            ("rules_version", "2.0.0"),
            ("configuration_id", "alternate"),
            ("season_id", "other-season"),
            ("commitment_id", "commitment-other"),
            ("bot_strategy_json", '{"opponent":"v2"}'),
        )
        # Reject each decoded start/terminal authority mismatch independently.
        for field, value in changed_authority:
            with self.subTest(field=field):
                changed = replace(terminal_event, **{field: value})
                with self.assertRaisesRegex(ConflictError, "authority"):
                    policy.project_day((start_event, changed), player_id=self.player_id, game_id=self.rule.game_id, utc_day=start_event.utc_day)
        # Reject a decoded completion clock that precedes its canonical start instant.
        early_terminal = replace(terminal_event, occurred_at="2026-08-31T12:29:59Z")
        with self.assertRaisesRegex(ConflictError, "time precedes"):
            policy.project_day((start_event, early_terminal), player_id=self.player_id, game_id=self.rule.game_id, utc_day=start_event.utc_day)
        # Reject a second terminal even when its physical and operation identities are unique.
        second_terminal = replace(terminal_event, event_id="event-second-terminal", idempotency_key="ranked-done-second-terminal", request_fingerprint="3" * 64)
        with self.assertRaisesRegex(ConflictError, "multiple terminal"):
            policy.project_day((start_event, terminal_event, second_terminal), player_id=self.player_id, game_id=self.rule.game_id, utc_day=start_event.utc_day)
        # Count any prohibited score execution over a corrupt decoded journal.
        score_calls = []

        def counting_score(_facts):
            # Record an execution that must remain unreachable.
            score_calls.append(True)
            return policy.ChallengeScore(points=1_000, formula_inputs={})

        counting_rule = policy.ChallengeRule(game_id=self.rule.game_id, rules_version=self.rule.rules_version, configuration_id=self.rule.configuration_id, score=counting_score)
        corrupt_terminal = replace(terminal_event, configuration_id="alternate")
        generated_before = self.events.calls
        digest = hashlib.sha256(b"corrupt-terminal-retry").hexdigest()
        # Validate the complete journal before scoring or allocating a terminal identity.
        with self.assertRaisesRegex(ConflictError, "authority"):
            policy.complete_ranked((start_event, corrupt_terminal), rule=counting_rule, player_id=self.player_id, run_id=start_event.run_id, completed_at=self.now + timedelta(minutes=10), idempotency_key="ranked-done-after-corruption", performance_facts={"cleared": 10, "mistakes": 0}, action_digest=digest, validation_outcome=policy.ACCEPTED, new_event_id=self.events)
        self.assertEqual((score_calls, self.events.calls), ([], generated_before))

    # Require the prototype source and event contract to have no token/storage surface.
    def test_policy_has_structural_wallet_and_provider_separation(self):
        # Require the production registry to remain explicitly empty and immutable.
        self.assertEqual(dict(policy.PRODUCTION_RULE_REGISTRY), {})
        with self.assertRaises(TypeError):
            policy.PRODUCTION_RULE_REGISTRY["synthetic_challenge"] = self.rule
        # Parse the exact implementation module currently under test.
        tree = ast.parse(inspect.getsource(policy))
        # Collect every imported module path.
        imports = set()
        # Inspect each import syntax node.
        for node in ast.walk(tree):
            # Record normal imports.
            if isinstance(node, ast.Import):
                # Add every imported module name.
                imports.update(alias.name for alias in node.names)
            # Record from-import module ownership.
            elif isinstance(node, ast.ImportFrom):
                # Add the source module when present.
                imports.add(node.module or "")
        # Reject every wallet, ledger, player, storage, route, or game import.
        self.assertFalse(any(fragment in module for module in imports for fragment in ("ledger", "players", "storage", "router", "casino.games")), imports)
        # Build one ranked-start record for exact field inspection.
        record = self.start((), "ranked-start-separation").events[0].to_record()
        # Require the exact approved Challenge event field inventory.
        self.assertEqual(tuple(record), policy.EVENT_FIELDS)
        # Require the future season/commitment/bot audit fields without active secrets.
        self.assertEqual((record["season_id"], record["commitment_id"], record["bot_strategy_json"]), ("synthetic-season-2026", "commitment-synthetic-001", "{}"))
        # Reject token/wager/balance/payout/amount fields categorically.
        self.assertTrue(set(record).isdisjoint({"amount", "balance", "tokens", "wager", "payout", "ledger_event_id", "transaction_type"}))


# Run the focused suite directly without starting a listener or provider.
if __name__ == "__main__":
    # Exit through unittest's ordinary status contract.
    unittest.main()
