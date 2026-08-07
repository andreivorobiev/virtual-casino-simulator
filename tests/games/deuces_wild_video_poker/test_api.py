"""Focused session, ledger, retry, and reload tests for Deuces Wild issue #92."""

# Import deep-copy support so fake persistence behaves like a JSON document boundary.
import copy
# Import the standard unit-test runner for dependency-free focused execution.
import unittest

# Import public conflict, lookup, and validation errors for precise boundary assertions.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import the current router so tests exercise the shared session-resolution boundary.
from casino.router import Router
# Import only the isolated game API and engine owned by issue #92.
from casino.games.deuces_wild_video_poker import api, engine


# Provide player-scoped persistence, ledger, and wallet ports without touching shared data.
class FakeCasino:
    # Initialize deterministic state and balances for the two isolated test players.
    def __init__(self):
        # Store game/player state documents by their complete persistence key.
        self.states = {}
        # Store immutable fake ledger events in append order.
        self.events = []
        # Keep balances inside the ledger adapter so game code cannot mutate them directly.
        self.balances = {"session-player": 100.0, "other-player": 100.0}
        # Count events for stable local ledger identifiers.
        self.sequence = 0

    # Build the same two-dimensional key accepted by the state-store port.
    def state_key(self, game_id, player_id):
        # Return an immutable tuple so games and players cannot share documents accidentally.
        return game_id, player_id

    # Return the live stored document only for explicit crash-window simulation in tests.
    def stored_state(self, player_id):
        # Resolve this game's player-scoped document without copying its marker fields.
        return self.states[self.state_key(engine.GAME_ID, player_id)]

    # Load a deep copy so service mutations require an explicit save operation.
    def load_state(self, game_id, player_id, factory):
        # Resolve the complete persistence key for this game and authenticated player.
        key = self.state_key(game_id, player_id)
        # Return a detached stored document or a detached fresh default.
        return copy.deepcopy(self.states.get(key, factory()))

    # Save a deep copy so later request objects cannot mutate durable state implicitly.
    def save_state(self, game_id, player_id, state):
        # Persist only beneath the complete game/player key supplied by the service.
        self.states[self.state_key(game_id, player_id)] = copy.deepcopy(state)

    # Commit one signed fake ledger movement with the production public event shape.
    def transact(self, player_id, amount, transaction_type, game=None, round_id=None, details=None):
        # Reject unknown player identities instead of silently creating wallet state.
        if player_id not in self.balances:
            # Surface a test failure if the service escapes its authenticated player set.
            raise AssertionError(f"unknown fake player: {player_id}")
        # Normalize signed token movement to the shared ledger's two-decimal precision.
        signed_amount = round(float(amount), 2)
        # Read the pre-transaction balance for ledger audit semantics.
        before = self.balances[player_id]
        # Calculate the only balance mutation performed by this fake ledger.
        after = round(before + signed_amount, 2)
        # Reject overdrafts because these focused scenarios never request insufficient funds.
        if after < 0:
            # Fail the test adapter at the same pre-commit boundary as the real ledger.
            raise AssertionError("fake ledger overdraft")
        # Advance the stable event sequence only for a committed movement.
        self.sequence += 1
        # Persist the wallet result atomically with the event in this in-memory adapter.
        self.balances[player_id] = after
        # Build every public ledger field used by service validation and audit assertions.
        event = {
            "ts": "2026-07-14T18:00:00.000Z",  # Keep event time deterministic.
            "ledger_id": f"led_{self.sequence}",  # Give each movement a stable identity.
            "player_id": player_id,  # Record the authenticated wallet owner.
            "game": game,  # Record the isolated game identity.
            "round_id": round_id,  # Record the deterministic game round identity.
            "transaction_type": transaction_type,  # Record wager or returned-credit semantics.
            "amount": signed_amount,  # Record the signed balance movement.
            "balance_before": before,  # Preserve the balance audit boundary.
            "balance_after": after,  # Preserve the resulting balance audit boundary.
            "details": copy.deepcopy(details or {}),  # Detach structured idempotency proof.
        }
        # Append the event once after its wallet mutation is accepted.
        self.events.append(event)
        # Return a detached event like a storage provider response.
        return copy.deepcopy(event)

    # Route a positive wager amount through the signed fake transaction boundary.
    def debit(self, player_id, amount, transaction_type, game=None, round_id=None, details=None):
        # Commit the wager as one negative ledger movement.
        return self.transact(player_id, -abs(float(amount)), transaction_type, game, round_id, details)

    # Route a positive returned-credit amount through the signed fake transaction boundary.
    def credit(self, player_id, amount, transaction_type, game=None, round_id=None, details=None):
        # Commit the returned credits as one positive ledger movement.
        return self.transact(player_id, abs(float(amount)), transaction_type, game, round_id, details)

    # Read bounded player history through the same callable shape as the shared ledger.
    def read_ledger(self, player_id=None, limit=100):
        # Filter another player's rows before applying the requested history bound.
        selected = [event for event in self.events if player_id is None or event["player_id"] == player_id]
        # Return detached chronological events so service validation cannot alter proof.
        return copy.deepcopy(selected[-limit:])

    # Return the read-only current-player shape included by game responses.
    def get_player(self, player_id):
        # Expose only authenticated identity and the ledger-managed test balance.
        return {"player_id": player_id, "balance": self.balances[player_id]}


# Verify real route dispatch, session isolation, and exactly-once ledger recovery.
class DeucesWildVideoPokerApiTests(unittest.TestCase):
    # Build fresh fake ports and a game-local router before every test.
    def setUp(self):
        # Create isolated persistence and wallet state for this test case.
        self.fake = FakeCasino()
        # Store the authenticated request context used by the shared router boundary.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}
        # Build the first service and router over the shared fake durable state.
        self.rebuild_runtime()

    # Reconstruct a service and router while retaining only fake durable state and ledger proof.
    def rebuild_runtime(self, seed="api:paying-seed-0001", debit=None, credit=None):
        # Inject deterministic time, cards, persistence, ledger, and player-read ports.
        self.service = api.DeucesWildVideoPokerService(
            load_state=self.fake.load_state,  # Reuse player-scoped durable documents.
            save_state=self.fake.save_state,  # Reuse explicit durable writes.
            debit=debit or self.fake.debit,  # Preserve or deliberately interrupt ledger-only wager settlement.
            credit=credit or self.fake.credit,  # Preserve or deliberately interrupt ledger-only payout settlement.
            read_ledger=self.fake.read_ledger,  # Enable crash-window proof recovery.
            get_player=self.fake.get_player,  # Return the ledger-managed balance snapshot.
            clock=lambda: "2026-07-14T18:00:00.000Z",  # Freeze lifecycle timestamps.
            seed_factory=lambda action_id: seed,  # Produce the requested deterministic test deal plan.
        )
        # Create a fresh real router to prove registration survives service reconstruction.
        self.router = Router()
        # Register only the isolated issue #92 routes without touching shared discovery files.
        api.register(self.router, service=self.service)

    # Dispatch one request through the current real router and authenticated context.
    def call(self, path, body=None, method="POST"):
        # Use a fresh context mapping because the router publishes resolved identity into it.
        return self.router.dispatch(method, path, body or {}, context=copy.deepcopy(self.context))

    # Return ledger rows matching one game-owned transaction type.
    def events_of_type(self, transaction_type):
        # Filter immutable event history without relying on event order.
        return [event for event in self.fake.events if event["transaction_type"] == transaction_type]

    # Confirm hostile caller IDs cannot override the session and debit recovery is exactly once.
    def test_session_binding_and_reconstructed_deal_retry_are_exactly_once(self):
        # Submit conflicting body and query identities beneath one bound session.
        first = self.call(
            "/api/v1/games/deuces-wild-video-poker/rounds?player_id=other-player",  # Supply the hostile query identity.
            {"player_id": "other-player", "action_id": "deal-retry-0001", "wager": 2},  # Supply the hostile body identity.
        )
        # Read the persisted authenticated-player document for a marker-gap simulation.
        stored = self.fake.stored_state("session-player")
        # Simulate loss of the post-debit completion marker after the ledger committed.
        stored["active_round"]["wager_status"] = "pending"
        # Remove cached event identity so recovery must scan immutable ledger history.
        stored["active_round"].pop("wager_ledger_id", None)
        # Reconstruct all process-local service and route objects over durable proof.
        self.rebuild_runtime()
        # Replay the same semantic request with the same malicious caller identity.
        second = self.call(
            "/api/v1/games/deuces-wild-video-poker/rounds?player_id=other-player",  # Repeat the hostile query identity.
            {"player_id": "other-player", "action_id": "deal-retry-0001", "wager": 2},  # Repeat identical action semantics.
        )
        # Verify both responses retain the authenticated session's stable round identity.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify the public round owner is never selected from body or query input.
        self.assertEqual("session-player", second["round"]["player_id"])
        # Verify the response player snapshot follows the same authenticated identity.
        self.assertEqual("session-player", second["player"]["player_id"])
        # Verify reconstructed recovery is explicitly reported as a replay.
        self.assertTrue(second["replayed"])
        # Collect the aggregate wager movements after both attempts.
        debits = self.events_of_type("DWVP_WAGER_DEBIT")
        # Verify exactly one wager movement exists across the marker gap and retry.
        self.assertEqual(1, len(debits))
        # Verify the wager uses the required negative signed ledger semantics.
        self.assertEqual(-2.0, debits[0]["amount"])
        # Verify audit balances reconcile exactly with the signed movement.
        self.assertEqual((100.0, 98.0), (debits[0]["balance_before"], debits[0]["balance_after"]))
        # Verify all ledger ownership fields bind to the authenticated game round.
        self.assertEqual(("session-player", engine.GAME_ID, first["round"]["round_id"]), (debits[0]["player_id"], debits[0]["game"], debits[0]["round_id"]))
        # Read structured idempotency proof from the committed wager event.
        details = debits[0]["details"]
        # Verify client and internal action identities remain separate and stable.
        self.assertEqual("deal-retry-0001", details["client_action_id"])
        # Verify the internal ledger key is derived from the deterministic round.
        self.assertEqual(f"{first['round']['round_id']}:wager", details["idempotency_key"])
        # Verify the fingerprint binds the normalized wager to the private deal plan.
        self.assertEqual("2.00", details["legacy_request_fingerprint"]["wager"])
        # Verify the private deal plan is represented only by a SHA-256 digest.
        self.assertEqual(64, len(details["legacy_request_fingerprint"]["deal_plan"]))
        # Verify the hostile caller never receives a persisted state document.
        self.assertNotIn(self.fake.state_key(engine.GAME_ID, "other-player"), self.fake.states)

    # Confirm raw OpenAPI wager bounds fail before state, entropy, or ledger access.
    def test_contract_wager_bounds_reject_before_state_or_ledger(self):
        # Probe values that would round into the accepted interval if validated too late.
        invalid_values = (0.009, engine.MAX_WAGER + 0.004)
        # Exercise both contract edges through the real registered route.
        for index, value in enumerate(invalid_values):
            # Preserve the raw candidate in focused failure diagnostics.
            with self.subTest(value=value):
                # Require the public validation error promised by the contract boundary.
                with self.assertRaises(ValidationError):
                    # Submit one distinct retry-safe action for the invalid raw wager.
                    self.call(
                        "/api/v1/games/deuces-wild-video-poker/rounds",  # Target the deal route.
                        {"action_id": f"wager-bound-{index:04d}", "wager": value},  # Preserve the raw edge value.
                    )
        # Verify rejected contract inputs cannot append any token movement.
        self.assertEqual([], self.fake.events)
        # Verify validation occurs before a player-scoped state document is loaded or saved.
        self.assertEqual({}, self.fake.states)
        # Verify the ledger-owned wallet remains unchanged after both requests.
        self.assertEqual(100.0, self.fake.balances["session-player"])

    # Confirm one action identity cannot be reused for changed inputs or another command.
    def test_conflicting_retry_and_cross_command_action_reuse_are_rejected(self):
        # Create the original wager and action mapping.
        started = self.call(
            "/api/v1/games/deuces-wild-video-poker/rounds",  # Target the deal route.
            {"action_id": "deal-conflict-0001", "wager": 1},  # Establish the original fingerprint.
        )
        # Reject the same action identity when its normalized wager changes.
        with self.assertRaises(ConflictError):
            # Replay a semantically different wager under the existing action id.
            self.call(
                "/api/v1/games/deuces-wild-video-poker/rounds",  # Reuse the original route.
                {"action_id": "deal-conflict-0001", "wager": 2},  # Change the fingerprint deliberately.
            )
        # Reject the deal action identity when reused as a hold command.
        with self.assertRaises(ConflictError):
            # Target the original round but deliberately collide with the deal identity.
            self.call(
                f"/api/v1/games/deuces-wild-video-poker/rounds/{started['round']['round_id']}/holds",  # Change the command.
                {"action_id": "deal-conflict-0001", "holds": [0]},  # Reuse the original action identity.
            )
        # Verify rejected conflicts cannot append another token movement.
        self.assertEqual(1, len(self.events_of_type("DWVP_WAGER_DEBIT")))
        # Verify rejected conflicts leave the ledger-managed balance unchanged.
        self.assertEqual(99.0, self.fake.balances["session-player"])

    # Confirm held positions remain reload-safe and private replacements stay private.
    def test_holds_survive_service_reload_and_replay_without_ledger_activity(self):
        # Start one deterministic round for the authenticated player.
        started = self.call(
            "/api/v1/games/deuces-wild-video-poker/rounds",  # Target the deal route.
            {"action_id": "holds-deal-0001", "wager": 1},  # Create the hold-test round.
        )
        # Store the opaque round id used by the hold route.
        round_id = started["round"]["round_id"]
        # Persist an unsorted complete hold set under its own retry identity.
        held = self.call(
            f"/api/v1/games/deuces-wild-video-poker/rounds/{round_id}/holds",  # Target the active round.
            {"action_id": "holds-save-0001", "holds": [4, 0, 2]},  # Submit the complete selection.
        )
        # Verify the engine canonicalizes held positions before persistence.
        self.assertEqual([0, 2, 4], held["round"]["holds"])
        # Reconstruct the process-local service and router over saved state.
        self.rebuild_runtime()
        # Load state through the authenticated GET route with a hostile query identity.
        reloaded = self.call(
            "/api/v1/games/deuces-wild-video-poker/state?player_id=other-player",  # Supply a hostile query identity.
            {"player_id": "other-player"},  # Supply a hostile body identity.
            method="GET",  # Exercise the reload-safe read route.
        )
        # Verify the reloaded active round retains the canonical held positions.
        self.assertEqual([0, 2, 4], reloaded["state"]["active_round"]["holds"])
        # Verify the GET route still reports only the bound session player.
        self.assertEqual("session-player", reloaded["player"]["player_id"])
        # Verify private replacement order never appears in the public state payload.
        self.assertNotIn("_draw_pool", reloaded["state"]["active_round"])
        # Replay the identical hold action after reconstruction.
        replayed = self.call(
            f"/api/v1/games/deuces-wild-video-poker/rounds/{round_id}/holds",  # Target the reloaded round.
            {"action_id": "holds-save-0001", "holds": [4, 0, 2]},  # Repeat identical action semantics.
        )
        # Verify the hold action is explicitly recognized as a replay.
        self.assertTrue(replayed["replayed"])
        # Verify holds and reload reads create no wager, refund, or payout movements.
        self.assertEqual(1, len(self.fake.events))

    # Confirm a pre-debit process crash cannot settle or pay before wager recovery.
    def test_draw_after_pre_debit_crash_commits_wager_before_payout(self):
        # Define a BaseException boundary that models abrupt process loss before debit.
        def crash_before_debit(*_args, **_kwargs):
            # Escape the service's ordinary exception cleanup exactly as process death would.
            raise SystemExit("simulated pre-debit process crash")
        # Rebuild the service with the one-shot crash boundary in place of ledger debit.
        self.rebuild_runtime(debit=crash_before_debit)
        # Interrupt the original deal after prepared cards are durable but before token movement.
        with self.assertRaises(SystemExit):
            # Start the request through the same real Router boundary used by clients.
            self.call(
                "/api/v1/games/deuces-wild-video-poker/rounds",  # Target the isolated deal route.
                {"action_id": "crash-deal-0001", "wager": 2},  # Prepare a known paying round without debiting.
            )
        # Read the faithfully persisted prepared round left by the simulated process loss.
        prepared = self.fake.stored_state("session-player")["active_round"]
        # Verify the crash window contains cards and a pending wager but no ledger proof.
        self.assertEqual(("pending", []), (prepared["wager_status"], self.fake.events))
        # Preserve the opaque prepared round id before rebuilding process-local objects.
        round_id = prepared["round_id"]
        # Reconstruct the normal service over the same durable state and empty ledger.
        self.rebuild_runtime()
        # Attempt the exact exploit path: draw directly without replaying deal or reading state.
        settled = self.call(
            f"/api/v1/games/deuces-wild-video-poker/rounds/{round_id}/draw",  # Target the prepared round.
            {"action_id": "crash-draw-0001"},  # Establish one retry-safe settlement identity.
        )
        # Verify settlement first recovered and completed the missing aggregate wager.
        self.assertEqual("complete", settled["round"]["wager_status"])
        # Verify immutable append order proves the debit happened before any returned credits.
        self.assertEqual(["DWVP_WAGER_DEBIT", "DWVP_PAYOUT_CREDIT"], [event["transaction_type"] for event in self.fake.events])
        # Verify the known paying fixture nets two tokens only after its two-token wager.
        self.assertEqual(([-2.0, 4.0], 102.0), ([event["amount"] for event in self.fake.events], self.fake.balances["session-player"]))

    # Confirm a paying draw recovers a lost credit marker without duplicating payout.
    def test_draw_and_reconstructed_payout_retry_credit_exactly_once(self):
        # Start the known deterministic plan whose full replacement hand is a straight.
        started = self.call(
            "/api/v1/games/deuces-wild-video-poker/rounds",  # Target the deterministic deal route.
            {"action_id": "payout-deal-0001", "wager": 2},  # Create the known paying plan.
        )
        # Store the deterministic round identity for settlement and replay.
        round_id = started["round"]["round_id"]
        # Draw all five replacements and settle through the real game route.
        first = self.call(
            f"/api/v1/games/deuces-wild-video-poker/rounds/{round_id}/draw",  # Target the paying round.
            {"action_id": "payout-draw-0001"},  # Establish the draw replay identity.
        )
        # Verify this deterministic fixture produces a positive two-times return.
        self.assertEqual((2, 4.0), (first["round"]["multiplier"], first["round"]["payout"]))
        # Read the stable outcome key across string and structured result contracts.
        result = first["round"]["result"]
        # Normalize the outcome during the additive contract migration.
        result_key = result["outcome"] if isinstance(result, dict) else result
        # Verify the known replacement plan settles as a straight.
        self.assertEqual("straight", result_key)
        # Read the archived stored document for a post-credit marker-gap simulation.
        stored = self.fake.stored_state("session-player")
        # Simulate loss of the completion marker after the ledger credit committed.
        stored["recent_rounds"][-1]["payout_status"] = "pending"
        # Remove cached credit identity so reconstructed recovery must scan the ledger.
        stored["recent_rounds"][-1].pop("payout_ledger_id", None)
        # Reconstruct service and routing objects while retaining durable cards and proof.
        self.rebuild_runtime()
        # Replay the exact draw action after the simulated marker gap.
        second = self.call(
            f"/api/v1/games/deuces-wild-video-poker/rounds/{round_id}/draw",  # Target the archived round.
            {"action_id": "payout-draw-0001"},  # Repeat identical draw semantics.
        )
        # Verify deterministic final cards remain identical across reconstruction.
        self.assertEqual(first["round"]["final_hand"], second["round"]["final_hand"])
        # Verify the reconstructed action is explicitly reported as a replay.
        self.assertTrue(second["replayed"])
        # Collect payout credits after initial settlement and reconstructed recovery.
        credits = self.events_of_type("DWVP_PAYOUT_CREDIT")
        # Verify exactly one returned-credit movement exists across both attempts.
        self.assertEqual(1, len(credits))
        # Verify returned credits use positive signed ledger semantics.
        self.assertEqual(4.0, credits[0]["amount"])
        # Verify wager then returned credits reconcile to the final wallet balance.
        self.assertEqual((98.0, 102.0, 102.0), (credits[0]["balance_before"], credits[0]["balance_after"], self.fake.balances["session-player"]))
        # Verify payout proof binds game, round, client action, and internal idempotency key.
        self.assertEqual((engine.GAME_ID, round_id, "payout-draw-0001", f"{round_id}:payout"), (credits[0]["game"], credits[0]["round_id"], credits[0]["details"]["client_action_id"], credits[0]["details"]["idempotency_key"]))
        # Verify result and returned-credit values participate in the payout fingerprint.
        self.assertEqual(result_key, credits[0]["details"]["legacy_request_fingerprint"]["result"])
        # Verify the exact returned credits are represented canonically in recovery proof.
        self.assertEqual("4.00", credits[0]["details"]["legacy_request_fingerprint"]["payout"])
        # Verify the round is no longer active after durable settlement.
        self.assertIsNone(second["state"]["active_round"])
        # Verify the settled round remains available in bounded reload history.
        self.assertEqual(round_id, second["state"]["recent_rounds"][-1]["round_id"])
        # Replay the original deal after settlement when private replacement cards are gone.
        deal_replay = self.call(
            "/api/v1/games/deuces-wild-video-poker/rounds",  # Target the original deal route.
            {"action_id": "payout-deal-0001", "wager": 2},  # Repeat the original wager semantics.
        )
        # Verify the durable private digest preserves the original deal replay identity.
        self.assertEqual((True, round_id), (deal_replay["replayed"], deal_replay["round"]["round_id"]))
        # Verify a completed-round deal replay cannot append another wager movement.
        self.assertEqual(1, len(self.events_of_type("DWVP_WAGER_DEBIT")))

    # Confirm losing retries remain settled without creating forbidden zero ledger rows.
    def test_losing_draw_and_recovery_create_no_payout_event(self):
        # Rebuild with a deterministic all-replacement plan that produces no qualifying hand.
        self.rebuild_runtime(seed="api:losing-seed-0000")
        # Start one low-cost round through the real session-bound route.
        started = self.call(
            "/api/v1/games/deuces-wild-video-poker/rounds",  # Target the isolated deal route.
            {"action_id": "losing-deal-0001", "wager": 1},  # Establish one debit and deterministic plan.
        )
        # Settle without holds so the known losing replacement hand is used.
        first = self.call(
            f"/api/v1/games/deuces-wild-video-poker/rounds/{started['round']['round_id']}/draw",  # Target the active round.
            {"action_id": "losing-draw-0001"},  # Establish the terminal retry identity.
        )
        # Verify the deterministic fixture lands on the stable losing paytable row.
        self.assertEqual(("no_win", 0.0), (first["round"]["result"], first["round"]["payout"]))
        # Verify losing settlement returns no fabricated zero-value ledger event.
        self.assertIsNone(first["payout"])
        # Simulate a stale payout marker even though no credit is required.
        self.fake.stored_state("session-player")["recent_rounds"][-1]["payout_status"] = "pending"
        # Reconstruct process-local state before exercising read-time recovery.
        self.rebuild_runtime(seed="api:losing-seed-0000")
        # Recover the terminal marker through the authenticated state endpoint.
        recovered = self.call("/api/v1/games/deuces-wild-video-poker/state", method="GET")
        # Verify recovery completes the marker without changing the losing outcome.
        self.assertEqual("complete", recovered["state"]["recent_rounds"][-1]["payout_status"])
        # Verify the wager remains the only ledger movement across draw and recovery.
        self.assertEqual(["DWVP_WAGER_DEBIT"], [event["transaction_type"] for event in self.fake.events])
        # Verify the player loses exactly the one-token wager and nothing else.
        self.assertEqual(99.0, self.fake.balances["session-player"])

    # Confirm an owed payout is recovered before another round can consume history space.
    def test_new_deal_recovers_pending_payout_before_admission(self):
        # Define a transient credit outage after final cards become durable.
        def fail_credit(*_args, **_kwargs):
            # Model a storage-provider failure without appending ledger proof.
            raise RuntimeError("simulated payout credit outage")
        # Rebuild with a healthy wager port and failing payout port.
        self.rebuild_runtime(credit=fail_credit)
        # Start the known paying two-token round normally.
        started = self.call(
            "/api/v1/games/deuces-wild-video-poker/rounds",  # Target the isolated deal route.
            {"action_id": "owed-deal-0001", "wager": 2},  # Establish the wager and paying card plan.
        )
        # Preserve its stable identity before simulating payout failure.
        owed_round_id = started["round"]["round_id"]
        # Surface the transient failure only after terminal cards have been saved.
        with self.assertRaises(RuntimeError):
            # Attempt payout settlement through the real draw route.
            self.call(
                f"/api/v1/games/deuces-wild-video-poker/rounds/{owed_round_id}/draw",  # Target the paying round.
                {"action_id": "owed-draw-0001"},  # Establish one retry-safe draw identity.
            )
        # Verify the owed round remains durable and explicitly pending recovery.
        self.assertEqual("pending", self.fake.stored_state("session-player")["recent_rounds"][-1]["payout_status"])
        # Reject a different new round while the same credit outage remains active.
        with self.assertRaises(RuntimeError):
            # Attempt to bypass the owed credit by dealing another hand directly.
            self.call(
                "/api/v1/games/deuces-wild-video-poker/rounds",  # Target new-round admission.
                {"action_id": "next-deal-0001", "wager": 1},  # Supply otherwise valid new action semantics.
            )
        # Verify failed recovery cannot append the next wager or evict the owed result.
        self.assertEqual(["DWVP_WAGER_DEBIT"], [event["transaction_type"] for event in self.fake.events])
        # Restore the healthy payout adapter over the same durable state.
        self.rebuild_runtime()
        # Retry the new deal so recovery and admission occur inside one action lock.
        admitted = self.call(
            "/api/v1/games/deuces-wild-video-poker/rounds",  # Retry new-round admission.
            {"action_id": "next-deal-0001", "wager": 1},  # Preserve the exact new action semantics.
        )
        # Verify the owed credit commits before the next round's wager debit.
        self.assertEqual(["DWVP_WAGER_DEBIT", "DWVP_PAYOUT_CREDIT", "DWVP_WAGER_DEBIT"], [event["transaction_type"] for event in self.fake.events])
        # Verify the prior round remains retained with its recovered completion marker.
        prior = next(item for item in admitted["state"]["recent_rounds"] if item["round_id"] == owed_round_id)
        # Verify payout recovery completed before the new active round was returned.
        self.assertEqual(("complete", "hold"), (prior["payout_status"], admitted["round"]["phase"]))

    # Confirm an ordinary rejected debit cannot leave a phantom actionable round.
    def test_rejected_wager_restores_clean_state_without_ledger_proof(self):
        # Remove available play tokens before starting a positive wager.
        self.fake.balances["session-player"] = 0.0
        # Reject the fake ledger overdraft at its pre-commit boundary.
        with self.assertRaises(AssertionError):
            # Attempt one wager whose prepared cards must be rolled back.
            self.call(
                "/api/v1/games/deuces-wild-video-poker/rounds",  # Target the isolated deal route.
                {"action_id": "funds-deal-0001", "wager": 1},  # Request more tokens than the player owns.
            )
        # Load the restored player document written by the service cleanup path.
        restored = self.fake.stored_state("session-player")
        # Verify no actionable round or replay mapping survives the rejected ledger call.
        self.assertEqual((None, {}), (restored["active_round"], restored["actions"]))
        # Verify rejected movement appends no ledger event and changes no balance.
        self.assertEqual(([], 0.0), (self.fake.events, self.fake.balances["session-player"]))

    # Confirm foreign and unknown rounds produce indistinguishable session-scoped failures.
    def test_foreign_round_is_private_to_its_authenticated_player(self):
        # Create one real persisted and wagered round directly for the other test player.
        foreign = self.service.start_round(
            "other-player",  # Select the separate direct-service identity.
            {"action_id": "foreign-deal-0001", "wager": 1},  # Create its isolated round.
        )
        # Store the opaque foreign identity used only to probe privacy behavior.
        foreign_round_id = foreign["round"]["round_id"]
        # Capture the foreign-round error returned beneath the bound session.
        with self.assertRaises(NotFoundError) as foreign_error:
            # Attempt to change holds on another player's real round.
            self.call(
                f"/api/v1/games/deuces-wild-video-poker/rounds/{foreign_round_id}/holds?player_id=other-player",  # Probe the foreign round.
                {"player_id": "other-player", "action_id": "foreign-hold-0001", "holds": [0]},  # Attempt caller override.
            )
        # Capture the error for a syntactically valid but nonexistent round.
        with self.assertRaises(NotFoundError) as missing_error:
            # Probe the same hold route with no corresponding player-owned state.
            self.call(
                "/api/v1/games/deuces-wild-video-poker/rounds/dwvp_missing000000000000000/holds",  # Probe an absent round.
                {"action_id": "missing-hold-0001", "holds": [0]},  # Use valid command semantics.
            )
        # Verify foreign and missing identities expose the same public error contract.
        self.assertEqual((missing_error.exception.code, missing_error.exception.status, missing_error.exception.message), (foreign_error.exception.code, foreign_error.exception.status, foreign_error.exception.message))
        # Verify the bound session also cannot draw the foreign round.
        with self.assertRaises(NotFoundError):
            # Attempt settlement while supplying the foreign player in both caller fields.
            self.call(
                f"/api/v1/games/deuces-wild-video-poker/rounds/{foreign_round_id}/draw?player_id=other-player",  # Probe foreign settlement.
                {"player_id": "other-player", "action_id": "foreign-draw-0001"},  # Attempt caller override.
            )
        # Verify rejected foreign probes append no session-player ledger events.
        self.assertEqual([], [event for event in self.fake.events if event["player_id"] == "session-player"])
        # Verify the other player's original wager remains the only committed movement.
        self.assertEqual(1, len(self.fake.events))
        # Verify foreign state remains intact beneath its original owner.
        self.assertEqual(foreign_round_id, self.fake.stored_state("other-player")["active_round"]["round_id"])

    # Confirm recovery rejects ledger rows whose semantic fingerprint was altered.
    def test_recovery_rejects_conflicting_ledger_proof_without_second_debit(self):
        # Start one wager and persist valid replay state.
        self.call(
            "/api/v1/games/deuces-wild-video-poker/rounds",  # Target the deal route.
            {"action_id": "proof-deal-0001", "wager": 2},  # Establish valid ledger proof.
        )
        # Read the stored round for a simulated lost post-ledger marker.
        stored = self.fake.stored_state("session-player")
        # Force wager reconciliation on the next reconstructed request.
        stored["active_round"]["wager_status"] = "pending"
        # Remove the cached ledger identity from persisted round state.
        stored["active_round"].pop("wager_ledger_id", None)
        # Alter immutable-looking proof to represent a conflicting prior semantic action.
        self.fake.events[0]["details"]["legacy_request_fingerprint"]["wager"] = "9.99"
        # Reconstruct all process-local service state before recovery.
        self.rebuild_runtime()
        # Reject conflicting proof rather than accepting it or issuing another debit.
        with self.assertRaises(ConflictError):
            # Replay the original action whose ledger proof no longer matches.
            self.call(
                "/api/v1/games/deuces-wild-video-poker/rounds",  # Target replay recovery.
                {"action_id": "proof-deal-0001", "wager": 2},  # Repeat original semantics.
            )
        # Verify strict proof validation leaves the event count exactly one.
        self.assertEqual(1, len(self.fake.events))
        # Verify the rejected recovery cannot change the post-wager balance.
        self.assertEqual(98.0, self.fake.balances["session-player"])


# Run this focused suite when invoked directly by the bounded worker.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
