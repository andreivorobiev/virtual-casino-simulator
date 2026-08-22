# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused exact-control schedule proofs extracted from the formal UI harness suite."""

# Run async helper seams without starting Chromium.
import asyncio
# Integrate the extracted proofs with the repository API harness.
import unittest
# Count exact per-control activation schedules.
from collections import Counter

# Exercise the production formal UI schedule owner without starting its CLI.
from tests import ui_50000


# Prove TEST-092 exact-control schedules and browser-operation complexity independently of aggregate fixtures.
class UI50000ControlScheduleTests(unittest.TestCase):
    # Prove exact Repeat ownership sums to one hundred while every isolated user keeps cycle zero as a fresh seed.
    def test_formal_repeat_plan_frontloads_capacity_without_replica_restarts(self):
        expected = {"keno": [100, 0, 0, 0, 0, 0], "bingo": [51, 49] + [0] * 19, "double_bonus_video_poker": [63, 37] + [0] * 15, "texas_holdem_practice_table": [90, 10] + [0] * 10, "sic_bo": [100]}  # Pin representative single- and multi-worker capacity boundaries.
        allocations = ui_50000.formal_allocations()  # Resolve the exact current 140-worker plan once.
        for game_id in ui_50000.REPEAT_CONTROL_SELECTORS:  # Audit every aggregate-short Repeat identity.
            module_source = (ui_50000.ROOT / "web" / "games" / f"{game_id}.js").read_text(encoding="utf-8")  # Read the exact registered frontend source owning this selector.
            selector = ui_50000.REPEAT_CONTROL_SELECTORS[game_id]  # Resolve the exact schedule identity under review.
            source_attribute = selector.strip("[]") if "data-testid" in selector else 'data-action="repeat"'  # Convert selector quoting into the product markup identity.
            self.assertIn(source_attribute, module_source, game_id)  # Bind every schedule identity to real product markup or handler code.
            game_allocations = [allocation for allocation in allocations if allocation[0] == game_id]  # Preserve stable replica order and per-user quota.
            shares = [ui_50000.formal_repeat_quota(game_id, allocation[2]) for allocation in game_allocations]  # Derive the exact local Repeat shares.
            self.assertEqual(sum(shares), ui_50000.CONTROL_ACTIVATION_FLOOR, game_id)  # Allocate the literal floor once, never once per replica.
            self.assertTrue(all(share <= allocation[3] - 1 for share, allocation in zip(shares, game_allocations)), game_id)  # Reserve every owning user's local cycle zero.
            self.assertFalse(ui_50000.should_schedule_repeat(game_id, 0, 0, True), game_id)  # Require the first settlement to seed real history.
        for game_id, shares in expected.items():  # Pin the reviewed capacity-frontloaded edge cases exactly.
            self.assertEqual([ui_50000.formal_repeat_quota(game_id, replica) for replica in range(len(shares))], shares, game_id)  # Reject a future round-robin overrun.

    # Prove Bingo preserves route-local replay history only for its exact share while every remaining fresh rank reaches one real catalog entry.
    def test_bingo_same_mount_repeat_and_navigation_plan_is_exact(self):
        replay_local_ranges = {}  # Preserve the exact same-mount replay positions independently per isolated user.
        ordinary_ranks = []  # Collect the globally gapless fresh strategy schedule.
        navigation_counts = Counter()  # Count only real catalog entry controls on navigated cycles.
        allocations = [allocation for allocation in ui_50000.formal_allocations() if allocation[0] == "bingo"]  # Resolve the immutable twenty-one-worker Bingo plan.
        for game_id, _game_index, replica_index, quota, cycle_start in allocations:  # Traverse every assigned Bingo ID exactly once.
            local_replays = []  # Preserve this user's consecutive same-mount replay window.
            for local_ordinal in range(quota):  # Reproduce the production per-cycle decision.
                game_ordinal = ui_50000.coverage_ordinal(game_id, local_ordinal, cycle_start + local_ordinal, True)  # Resolve the continuous game rank.
                if ui_50000.should_schedule_repeat(game_id, local_ordinal, replica_index, True):  # Match the production route-preservation gate.
                    local_replays.append(local_ordinal)  # Credit one real replay cycle without fabricating navigation.
                    continue  # Leave fresh scheduling and catalog activation untouched.
                ordinary = ui_50000.formal_ordinary_ordinal(game_id, game_ordinal, local_ordinal, replica_index)  # Collapse exactly prior replay-only cycles.
                ordinary_ranks.append(ordinary)  # Preserve the fresh rank for continuity proof.
                navigation_counts[ui_50000.bingo_navigation_entry(ordinary)] += 1  # Credit the exact real catalog control scheduled for this cycle.
            replay_local_ranges[replica_index] = local_replays  # Store the complete per-user replay window.
        self.assertEqual(replay_local_ranges[0], list(range(1, 52)))  # Require replica zero's seed followed by fifty-one consecutive same-mount replays.
        self.assertEqual(replay_local_ranges[1], list(range(1, 50)))  # Require replica one's seed followed by forty-nine consecutive same-mount replays.
        self.assertTrue(all(not values for replica, values in replay_local_ranges.items() if replica > 1))  # Forbid replay restarts on later isolated users.
        self.assertEqual(sum(map(len, replay_local_ranges.values())), ui_50000.CONTROL_ACTIVATION_FLOOR)  # Spend exactly one hundred real replay cycles.
        self.assertEqual(ordinary_ranks, list(range(987)))  # Preserve every remaining fresh rank once without aliases or holes.
        self.assertEqual(navigation_counts, Counter({"open": 887, "nav": 100}))  # Keep both Bingo catalog controls above their literal floor.
        self.assertEqual(sum(navigation_counts.values()), 987)  # Navigate once for every fresh cycle and never during same-mount replay.
        with self.assertRaisesRegex(AssertionError, "invalid Bingo ordinary ordinal"):
            ui_50000.bingo_navigation_entry(-1)  # Reject stale range arithmetic before any public navigation.
        with self.assertRaisesRegex(AssertionError, "invalid Bingo ordinary ordinal"):
            ui_50000.bingo_navigation_entry(987)  # Reject a fresh rank beyond the exact post-replay inventory.

    # Prove Acey-Deucey keeps its complete Repeat share on one mount and retains exact real navigation floors afterward.
    def test_acey_deucey_seed_limit_same_mount_repeat_and_navigation_plan_are_exact(self):
        from casino.games.acey_deucey.engine import RECENT_ROUND_LIMIT  # Bind the harness ceiling to the product's complete recoverable history window.

        self.assertEqual(ui_50000.ACEY_DEUCEY_REPEAT_SEED_LIMIT, RECENT_ROUND_LIMIT)  # Reject drift between bounded seed evidence and public history capacity.
        self.assertEqual(ui_50000.SAME_MOUNT_REPEAT_GAME_IDS, frozenset({"acey_deucey", "bingo"}))  # Limit route preservation to the two reviewed transient replay owners.
        allocations = [allocation for allocation in ui_50000.formal_allocations() if allocation[0] == "acey_deucey"]  # Resolve exact worker eighty-five ownership.
        self.assertEqual(len(allocations), 1)  # Preserve one isolated Acey-Deucey worker and its unchanged duration profile.
        replay_locals = []  # Collect only exact same-mount Repeat cycles.
        ordinary_ranks = []  # Preserve all remaining fresh ranks without aliases or holes.
        navigation_counts = Counter()  # Count real catalog entries plus lobby returns on navigated cycles.
        for game_id, _game_index, replica_index, quota, cycle_start in allocations:  # Traverse all 1,087 exact assigned IDs once.
            self.assertEqual(quota, 1087)  # Bind navigation arithmetic to the frozen one-worker allocation.
            for local_ordinal in range(quota):  # Reproduce the production route-preservation decision.
                game_ordinal = ui_50000.coverage_ordinal(game_id, local_ordinal, cycle_start + local_ordinal, True)  # Resolve the continuous game rank.
                if ui_50000.should_schedule_repeat(game_id, local_ordinal, replica_index, True):  # Match the exact local1..100 replay share.
                    replay_locals.append(local_ordinal)  # Credit one real same-mount Repeat case.
                    continue  # Forbid fabricated navigation on replay-only cycles.
                ordinary = ui_50000.formal_ordinary_ordinal(game_id, game_ordinal, local_ordinal, replica_index)  # Collapse the exact Repeat prefix.
                ordinary_ranks.append(ordinary)  # Preserve gapless fresh strategy ownership.
                navigation_counts[ui_50000.acey_deucey_navigation_entry(ordinary)] += 1  # Credit the scheduled public game entry.
                navigation_counts["lobby"] += 1  # Every navigated case first returns through the real Lobby control.
        self.assertEqual(replay_locals, list(range(1, 101)))  # Keep exactly one hundred consecutive replay cycles after local seed zero.
        self.assertEqual(ordinary_ranks, list(range(987)))  # Preserve exactly 987 fresh ranks including seed rank zero.
        self.assertEqual(navigation_counts, Counter({"lobby": 987, "open": 887, "nav": 100}))  # Keep all three exact shell controls above the literal floor.
        with self.assertRaisesRegex(AssertionError, "invalid Acey-Deucey ordinary ordinal"):
            ui_50000.acey_deucey_navigation_entry(-1)  # Reject stale negative fresh-rank arithmetic.
        with self.assertRaisesRegex(AssertionError, "invalid Acey-Deucey ordinary ordinal"):
            ui_50000.acey_deucey_navigation_entry(987)  # Reject a rank beyond the exact post-replay inventory.

    # Prove Roulette setting mutations are deterministic, distributed off Rebet, and sufficient for literal control floors.
    def test_roulette_serialized_settings_schedule_reaches_exact_control_floors(self):
        mode_probes = [ordinal for ordinal in range(1087) if ui_50000.should_probe_roulette_mode(ordinal)]  # Enumerate every opposite-mode probe.
        zero_rotations = [ordinal for ordinal in range(1087) if ui_50000.should_rotate_roulette_zero_rule(ordinal)]  # Enumerate every zero-rule transition.
        self.assertEqual(mode_probes, list(range(202, 1085, 18)))  # Distribute exactly fifty probes beyond primary Rebet ownership.
        self.assertEqual(len(mode_probes) * 2, ui_50000.CONTROL_ACTIVATION_FLOOR)  # Guarantee the floor from each real probe plus its serialized scheduled-mode restoration, independent of initial mode transitions.
        self.assertEqual(len(zero_rotations), ui_50000.CONTROL_ACTIVATION_FLOOR)  # Guarantee the zero-rule floor with one hundred scheduled changes.
        self.assertTrue(all(ordinal > 100 for ordinal in mode_probes + zero_rotations))  # Never change server settings while the primary worker owns open Rebet wagers.
        self.assertFalse(set(mode_probes).intersection(zero_rotations))  # Keep every scheduled cycle to at most one probe before exact mode enforcement.

    # Prove Keno and Sic Bo retain every literal board floor after exactly one hundred sole-terminal Repeat cycles.
    def test_formal_board_schedules_exceed_floor_after_repeat_capacity(self):
        keno_counts = Counter()  # Count real individual Keno pointer targets under the exact six-worker plan.
        sic_bo_counts = Counter()  # Count real Sic Bo wager targets under the exact one-worker plan.
        repeat_counts = Counter()  # Prove each affected game spends exactly the assigned Repeat floor.
        fresh_counts = Counter()  # Prove the remaining 987 cycles stay globally continuous.
        for game_id, _game_index, replica_index, quota, cycle_start in ui_50000.formal_allocations():  # Traverse immutable worker ranges without browser work.
            if game_id not in {"keno", "sic_bo"}:  # Limit arithmetic to the two repaired aggregate board deficits.
                continue  # Preserve a focused executable proof.
            for local_ordinal in range(quota):  # Reproduce every exact assigned cycle once.
                game_ordinal = ui_50000.coverage_ordinal(game_id, local_ordinal, cycle_start + local_ordinal, True)  # Resolve the same formal rank used by the worker.
                if ui_50000.should_schedule_repeat(game_id, local_ordinal, replica_index, True):  # Remove this user's exact replay-only cycles.
                    repeat_counts[game_id] += 1  # Count the sole-terminal Repeat allocation.
                    continue  # Do not credit fresh board controls during replay.
                ordinary = ui_50000.formal_ordinary_ordinal(game_id, game_ordinal, local_ordinal, replica_index)  # Collapse replicas and Repeat gaps into one fresh rank.
                self.assertEqual(ordinary, fresh_counts[game_id], (game_id, replica_index, local_ordinal))  # Require exact continuity without aliasing or holes.
                fresh_counts[game_id] += 1  # Advance the canonical fresh-cycle inventory.
                if game_id == "keno":  # Reproduce the production quick-pick and individual-cell schedule.
                    mode = ordinary % 16  # Apply the two quick modes and fourteen individual modes.
                    if mode >= 2:  # Credit only actual individual number clicks.
                        number_start, replacement_start = ui_50000.keno_number_schedule(ordinary)  # Resolve the same gapless cell slice as production.
                        for offset in range(ui_50000.KENO_NUMBER_CLICKS_PER_CYCLE):  # Spend the checked-in exact pointer budget.
                            keno_counts[(number_start + offset) % 80] += 1  # Rotate across all eighty rendered cells.
                        if mode == 2:  # Reproduce the five-cell rebuild after the real Clear Selection action.
                            for offset in range(5):  # Restore one legal bounded ticket.
                                keno_counts[(replacement_start + offset) % 80] += 1  # Credit only the next five gapless replacement clicks.
                else:  # Reproduce the Sic Bo fresh wager and first-hundred ordinary Clear schedule.
                    wager_start, replacement_index = ui_50000.sic_bo_wager_schedule(ordinary)  # Resolve the shared gapless action slice.
                    for offset in range(ui_50000.SIC_BO_WAGER_CLICKS_PER_CYCLE):  # Spend five distinct real bets per fresh shake.
                        sic_bo_counts[(wager_start + offset) % 50] += 1  # Rotate across all fifty wager identities.
                    if replacement_index is not None:  # Preserve the Clear control's own literal ordinary-cycle floor.
                        sic_bo_counts[replacement_index % 50] += 1  # Credit the one real post-clear replacement wager.
        self.assertEqual(repeat_counts, Counter({"keno": 100, "sic_bo": 100}))  # Require exactly one hundred replays per affected game.
        self.assertEqual(fresh_counts, Counter({"keno": 987, "sic_bo": 987}))  # Preserve every non-Repeat cycle without gaps.
        self.assertEqual((len(keno_counts), min(keno_counts.values()), max(keno_counts.values())), (80, 100, 101))  # Reach the floor exactly through nine ordinary clicks plus real Clear replacements.
        self.assertEqual((len(sic_bo_counts), min(sic_bo_counts.values()), max(sic_bo_counts.values())), (50, 100, 101))  # Reach the floor exactly through five ordinary bets plus real Clear replacements.

    # Prove the time-balanced Roulette plan covers both mode inventories while moving autoplay off the primary Rebet range.
    def test_roulette_mode_relative_schedules_exceed_every_literal_floor(self):
        from casino.games.roulette.rules import catalog as roulette_catalog, roulette_numbers  # Bind browser inventory arithmetic to the exact production rules catalog.

        frontend_source = (ui_50000.ROOT / "web" / "games" / "roulette.js").read_text(encoding="utf-8")  # Read the renderer that owns the raw selector union.
        self.assertIn("catalog.filter(bet => bet.layout_kind !== 'outside' && bet.type !== 'straight')", frontend_source)  # Bind hotspot counts to the production filtering rule.
        self.assertIn("['red', 'black', 'odd', 'even', 'low', 'high'].map(type => `<button type=\"button\" data-outbtn=", frontend_source)  # Bind the six duplicate fast-bet targets to source.
        self.assertIn("['snake', 'voisins', 'tiers', 'orphelins', 'jeu_zero', 'neighbors', 'final', 'complete'].map(type => `<button type=\"button\" data-call=", frontend_source)  # Bind the eight racetrack call targets to source.
        for mode, expected in ui_50000.ROULETTE_SPECIAL_COUNTS.items():  # Derive exact raw mode inventories from source-owned catalog rows and fixed render groups.
            hotspots = sum(row.get("layout_kind") != "outside" and row.get("type") != "straight" for row in roulette_catalog(mode))  # Match the production hotspot filter byte-for-byte.
            raw_special_count = hotspots + 6 + 3 + 3 + 6 + 8  # Add table outside, dozen, column, duplicate fast-bet, and call controls rendered by source.
            self.assertEqual(raw_special_count, expected, mode)  # Reject stale constants before formal browser dispatch.
            self.assertEqual(len(roulette_numbers(mode)), ui_50000.ROULETTE_NUMBER_COUNTS[mode], mode)  # Bind each straight-number count to the production wheel helper.
        number_counts = {mode: Counter() for mode in ui_50000.ROULETTE_NUMBER_COUNTS}  # Count stable number positions independently per wheel inventory.
        special_counts = {mode: Counter() for mode in ui_50000.ROULETTE_SPECIAL_COUNTS}  # Count stable special positions independently per wheel inventory.
        mode_cycles = Counter()  # Bind the schedule to the exact 551/536 capacity split.
        autoplay_ranks = []  # Preserve only cycles accepted by the existing first-hundred autoplay helper.
        for game_ordinal in range(1087):  # Reproduce every exact Roulette cycle once without browser work.
            mode = ui_50000.roulette_mode_for_ordinal(game_ordinal)  # Resolve the same contiguous mode assignment as production.
            mode_cycles[mode] += 1  # Count exact inventory ownership.
            number_start, number_clicks = ui_50000.roulette_number_schedule(game_ordinal)  # Resolve the cumulative number slice.
            for offset in range(number_clicks):  # Credit only scheduled real number clicks.
                number_counts[mode][(number_start + offset) % ui_50000.ROULETTE_NUMBER_COUNTS[mode]] += 1  # Rotate within the exact mode-owned inventory.
            special_start, special_clicks = ui_50000.roulette_special_schedule(game_ordinal)  # Resolve the cumulative special slice.
            for offset in range(special_clicks):  # Credit only scheduled real special clicks.
                special_counts[mode][(special_start + offset) % ui_50000.ROULETTE_SPECIAL_COUNTS[mode]] += 1  # Rotate within the exact mode-owned inventory.
            autoplay_ordinal = ui_50000.roulette_autoplay_ordinal(game_ordinal)  # Apply the time-balanced ordinal translation.
            if autoplay_ordinal < ui_50000.CONTROL_ACTIVATION_FLOOR:  # Match the shared autoplay helper's exact acceptance window.
                autoplay_ranks.append((game_ordinal, autoplay_ordinal))  # Preserve only scheduled session cycles.
        self.assertEqual(mode_cycles, Counter({"double": 551, "single": 536}))  # Pin the exact source-reviewed inventory split.
        self.assertEqual(set(number_counts["double"].values()), {100})  # Prove the dedicated schedule assigns all 38 double-zero numbers exactly the floor before terminal seed wagers add coverage.
        self.assertEqual(set(number_counts["single"].values()), {100})  # Prove the dedicated schedule assigns all 37 single-zero numbers exactly the floor before terminal seed wagers add coverage.
        self.assertEqual(set(special_counts["double"].values()), {100})  # Prove the dedicated schedule assigns all 139 raw double-zero specials exactly the floor.
        self.assertEqual(set(special_counts["single"].values()), {100})  # Prove the dedicated schedule assigns all 135 raw single-zero specials exactly the floor.
        self.assertEqual(autoplay_ranks, [(ordinal, ordinal - 101) for ordinal in range(101, 201)])  # Move exactly one hundred sessions away from ranks0..100.
        roulette_allocations = [allocation for allocation in ui_50000.formal_allocations() if allocation[0] == "roulette"]  # Read exact frozen replica boundaries for runtime-budget ownership.
        per_replica_budgets = []  # Preserve number, special, and autoplay work assigned to each measured worker.
        for _game, _game_index, replica, quota, cycle_start in roulette_allocations:  # Reproduce each formal worker's exact game-relative range.
            first = ui_50000.coverage_ordinal("roulette", 0, cycle_start, True)  # Resolve the first continuous Roulette rank.
            ranks = range(first, first + quota)  # Preserve the immutable contiguous per-replica interval.
            per_replica_budgets.append((replica, quota, sum(ui_50000.roulette_number_schedule(rank)[1] for rank in ranks), sum(ui_50000.roulette_special_schedule(rank)[1] for rank in ranks), sum(ui_50000.roulette_autoplay_ordinal(rank) < 100 for rank in ranks)))  # Count only scheduled real pointer/session work.
        self.assertEqual(per_replica_budgets, [(0,101,101,1414,0),(1,90,450,2160,90),(2,90,810,2565,10),(3,90,810,2566,0),(4,90,810,2520,0),(5,90,819,2675,0),(6,90,630,2250,0),(7,90,630,2250,0),(8,89,623,2314,0),(9,89,571,2225,0),(10,89,623,2225,0),(11,89,623,2236,0)])  # Remove 1,414 requests from primary Rebet ownership while preserving replica one's autoplay-heavy budget and bounded higher-margin shares.

    # Prove exact Roulette rotation acquires one collection count and performs only its O(clicks) nth actions.
    def test_roulette_exact_rotation_does_not_rescan_target_inventory(self):
        events = []  # Record collection creation, one count acquisition, and selected stable indices.

        class FakeCollection:  # Model one stable-order locator collection across API rerenders.
            async def count(self):
                events.append("count")  # Expose any repeated full-inventory acquisition.
                return 5  # Provide the exact reviewed fake inventory.

            def nth(self, index):
                events.append(("nth", index))  # Record O(clicks) target resolution only.
                return index  # Return the stable index as the fake locator.

        class FakePage:  # Provide only the one collection lookup owned by the helper.
            def locator(self, selector):
                events.append(("locator", selector))  # Record one public selector acquisition.
                return FakeCollection()  # Return the stable fake collection.

        async def fake_action(_page, target, _activated_counts):
            events.append(("click", target))  # Record one serialized real-action seam per scheduled target.

        asyncio.run(ui_50000.rotate_exact_control_group(FakePage(), "[data-target]", 5, 3, 3, Counter(), fake_action))  # Exercise one wrapping stable-order slice.
        self.assertEqual(events, [("locator", "[data-target]"), "count", ("nth", 3), ("click", 3), ("nth", 4), ("click", 4), ("nth", 0), ("click", 0)])  # Reject any O(clicks×controls) scan.


if __name__ == "__main__":  # Preserve direct focused execution for local diagnostics.
    unittest.main()  # Run only the extracted exact-control schedule proofs.
