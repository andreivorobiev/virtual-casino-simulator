# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Exact-control identities, schedules, and aggregate classification for TEST-092."""

# Calculate fair opportunity shares for mutually exclusive decisions.
import math

# Bind schedules to the same canonical catalog consumed by the browser harness.
from casino.config import GAMES


# Preserve canonical catalog order for exact global-cycle arithmetic.
GAME_IDS = tuple(game["id"] for game in GAMES)
# Require the issue-owned activation floor for every ordinarily reachable eligible control.
CONTROL_ACTIVATION_FLOOR = 100
# Bound Acey-Deucey formal seed traversal to the product's complete retained-history window.
ACEY_DEUCEY_REPEAT_SEED_LIMIT = 20
# Preserve route-local replay state only for games whose product teardown clears otherwise valid Repeat ownership.
SAME_MOUNT_REPEAT_GAME_IDS = frozenset({"acey_deucey", "bingo"})
# Bind every registered game to one explicit rendered-control strategy family. (TEST-092, issue #1050)
UI_STRATEGY_FAMILIES = {
    "roulette": "roulette", "slots": "slots", "keno": "keno", "bingo": "bingo", "blackjack": "blackjack", "baccarat": "baccarat",  # Bind the six primary game strategies.
    "multi_hand_video_poker": "draw_poker", "casino_war": "casino_war", "big_six_wheel": "wager_inputs", "dragon_tiger": "dragon_tiger",  # Bind shared and bespoke table families.
    "red_dog": "red_dog", "hi_lo": "hi_lo", "scratch_cards": "scratch_cards", "sic_bo": "sic_bo", "chuck_a_luck": "wager_inputs",  # Bind wager and terminal state-machine families.
    "craps": "craps", "jacks_or_better_video_poker": "draw_poker", "deuces_wild_video_poker": "draw_poker", "three_card_poker": "three_card_poker",  # Bind dice and draw-poker families.
    "texas_holdem_practice_table": "texas_holdem", "crown_and_anchor": "wager_inputs", "over_under_7": "wager_inputs", "plinko": "plinko",  # Bind practice and terminal wagering families.
    "fan_tan": "wager_inputs", "andar_bahar": "andar_bahar", "acey_deucey": "acey_deucey", "caribbean_stud": "caribbean_stud",  # Bind card and prediction families.
    "let_it_ride": "let_it_ride", "casino_holdem": "casino_holdem", "joker_poker": "draw_poker", "color_wheel": "simple_terminal",  # Bind remaining card and wheel families.
    "pai_gow_poker": "pai_gow_poker", "poker_dice": "simple_terminal", "boule": "simple_terminal", "faro": "simple_terminal",  # Bind manual-setting and simple terminal games.
    "trente_et_quarante": "simple_terminal", "pachinko": "simple_terminal", "coin_pusher": "simple_terminal", "marble_race": "simple_terminal",  # Bind simple settled-action games.
    "pattern_draw": "simple_terminal", "lucky_grid": "lucky_grid", "daily_draw_lab": "daily_draw_lab", "four_card_poker": "four_card_poker",  # Bind grid, draw, and poker families.
    "double_bonus_video_poker": "draw_poker", "mississippi_stud": "mississippi_stud", "teen_patti": "teen_patti",  # Complete the exact 46-game catalog mapping.
}
# Enumerate every implemented dispatch family so registry entries cannot name a silent no-op.
IMPLEMENTED_UI_STRATEGY_FAMILIES = frozenset({"acey_deucey", "andar_bahar", "baccarat", "bingo", "blackjack", "caribbean_stud", "casino_holdem", "casino_war", "craps", "daily_draw_lab", "dragon_tiger", "draw_poker", "four_card_poker", "hi_lo", "keno", "let_it_ride", "lucky_grid", "mississippi_stud", "pai_gow_poker", "plinko", "red_dog", "roulette", "scratch_cards", "sic_bo", "simple_terminal", "slots", "teen_patti", "texas_holdem", "three_card_poker", "wager_inputs"})
# Keep Double Bonus on the shared draw-poker state machine while addressing its established route-local attribute names.
DRAW_POKER_UI_CONTROLS = {"default": {"deal": '[data-action="deal"]', "hold_attribute": "data-hold-position", "draw": '[data-action="draw"]'}, "double_bonus_video_poker": {"deal": "[data-deal]", "hold_attribute": "data-hold", "draw": "[data-draw]"}}
# Rank visible Pai Gow cards from weakest through strongest while keeping the semi-wild Joker out of the low hand.
PAI_GOW_RANK_VALUES = {rank: value for value, rank in enumerate(("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"), start=2)}
# Describe the simple settled-action surfaces without weakening their rendered-control coverage.
SIMPLE_TERMINAL_UI_STRATEGIES = {
    "color_wheel": {"control_groups": (("[data-color]", 1), ("[data-chip]", 1)), "action": '[data-testid="color-wheel-spin"]', "repeat": '[data-testid="color-wheel-repeat"]'},  # Rotate every color and chip before spinning.
    "poker_dice": {"control_groups": (("[data-chip]", 1),), "action": '[data-testid="poker-dice-roll"]', "repeat": '[data-testid="poker-dice-repeat"]'},  # Rotate chips before rolling.
    "boule": {"control_groups": (("[data-bet],[data-number]", 2), ("[data-chip]", 1)), "action": '[data-testid="boule-spin"]', "repeat": '[data-action="repeat"]'},  # Touch two wager choices per cycle.
    "faro": {"control_groups": (("[data-rank]", 2), ("[data-chip]", 1)), "action": '[data-testid="faro-deal"]', "repeat": '[data-testid="faro-repeat"]'},  # Touch two ranks per cycle.
    "trente_et_quarante": {"control_groups": (("[data-bet]", 1), ("[data-chip]", 1)), "action": '[data-testid="teq-deal"]', "repeat": '[data-action="repeat"]'},  # Rotate all table choices and chips.
    "pachinko": {"control_groups": (("[data-chip]", 1),), "action": '[data-testid="pachinko-drop"]', "repeat": '[data-testid="pachinko-repeat"]'},  # Rotate chips before dropping.
    "coin_pusher": {"control_groups": (("[data-chip]", 1),), "action": '[data-testid="coin-pusher-drop"]', "repeat": '[data-testid="coin-pusher-repeat"]'},  # Rotate chips before dropping.
    "marble_race": {"control_groups": (("[data-bet]", 1), ("[data-marble]", 1), ("[data-chip]", 1)), "action": '[data-testid="marble-race-go"]', "repeat": '[data-testid="marble-race-repeat"]'},  # Rotate market, runner, and chip.
    "pattern_draw": {"control_groups": (("[data-bet]", 1), ("[data-chip]", 1)), "action": '[data-testid="pattern-draw-draw"]', "repeat": '[data-testid="pattern-draw-repeat"]'},  # Rotate pattern and chip.
}
# Bind every aggregate-short Repeat identity to the exact rendered selector audited in the registered module. (TEST-092, issue #1052)
REPEAT_CONTROL_SELECTORS = {
    "acey_deucey": '[data-action="repeat"]', "andar_bahar": '[data-action="repeat"]', "big_six_wheel": '[data-action="repeat"]',  # Bind the first three public replay actions.
    "bingo": '[data-testid="bingo-repeat"]', "caribbean_stud": '[data-action="repeat"]', "casino_holdem": '[data-action="repeat"]',  # Bind Bingo and two staged poker actions.
    "casino_war": '[data-action="repeat"]', "chuck_a_luck": '[data-action="repeat"]', "craps": '[data-testid="craps-repeat"]',  # Bind table and dice replay actions.
    "crown_and_anchor": '[data-action="repeat"]', "deuces_wild_video_poker": '[data-action="repeat"]', "double_bonus_video_poker": '[data-action="repeat"]',  # Bind symbol and draw-poker actions.
    "dragon_tiger": '[data-action="repeat"]', "fan_tan": '[data-action="repeat"]', "hi_lo": '[data-action="repeat"]',  # Bind prediction and card actions.
    "jacks_or_better_video_poker": '[data-action="repeat"]', "joker_poker": '[data-action="repeat"]', "keno": '[data-action="repeat"]',  # Bind draw-poker and Keno actions.
    "let_it_ride": '[data-action="repeat"]', "multi_hand_video_poker": '[data-action="repeat"]', "over_under_7": '[data-action="repeat"]',  # Bind staged and multi-hand actions.
    "plinko": '[data-action="repeat"]', "red_dog": '[data-action="repeat"]', "scratch_cards": '[data-action="repeat"]',  # Bind drop, card, and scratch actions.
    "sic_bo": '[data-action="repeat"]', "slots": '[data-action="repeat"]', "texas_holdem_practice_table": '[data-action="repeat"]',  # Bind dice, cabinet, and practice actions.
    "three_card_poker": '[data-action="repeat"]',  # Complete the exact failed Repeat inventory.
}
# Spend the exact executable pointer minima for the two repaired board schedules.
KENO_NUMBER_CLICKS_PER_CYCLE, SIC_BO_WAGER_CLICKS_PER_CYCLE = 9, 5
# Bind mode-owned real number inventories to the rendered Roulette table.
ROULETTE_NUMBER_COUNTS = {"single": 37, "double": 38}
# Bind mode-owned raw special inventories to the exact selector union.
ROULETTE_SPECIAL_COUNTS = {"single": 135, "double": 139}
# Model controls that share one rare decision state where activating one removes every alternative.
MUTUALLY_EXCLUSIVE_CONTROL_GROUPS = (frozenset(("casino_war::button[data-action=surrender]", "casino_war::button[data-action=war]")),)


# Resolve the canonical first global cycle for one game's exact 50,000-cycle catalog allocation.
def formal_game_cycle_start(game_id, total_cycles=50_000):
    game_index = GAME_IDS.index(game_id)  # Bind the range to checked-in catalog order.
    base_quota, extra_games = divmod(int(total_cycles), len(GAME_IDS))  # Reproduce exact allocator arithmetic.
    return game_index * base_quota + min(game_index, extra_games)  # Count every preceding allocation.


# Keep every formal per-game schedule globally continuous while preserving focused-run compatibility.
def coverage_ordinal(game_id, local_ordinal, global_cycle, formal=False):
    if formal:  # Remove replica-local resets only for the exact distributed plan.
        scheduled = int(global_cycle) - formal_game_cycle_start(game_id)  # Convert the global ID into one game rank.
        if scheduled < 0:  # Reject a stale worker range.
            raise AssertionError(f"formal cycle {global_cycle} precedes {game_id} allocation")  # Fail before scheduling controls.
        return scheduled  # Continue all formal schedules across replicas.
    return global_cycle if game_id == "roulette" else local_ordinal  # Preserve focused-run behavior.


# Split exactly one hundred Repeat cycles across isolated users while reserving local cycle zero.
def formal_repeat_quota(game_id, replica_index, allocations):
    if game_id not in REPEAT_CONTROL_SELECTORS:  # Limit work to the exact failed inventory.
        return 0  # Preserve unrelated strategies.
    remaining = CONTROL_ACTIVATION_FLOOR  # Allocate the literal floor once.
    for allocation in allocations:  # Traverse exact immutable replica capacities.
        allocated_game, _game_index, allocated_replica, quota, _cycle_start = allocation  # Unpack public metadata.
        if allocated_game != game_id:  # Ignore independent games.
            continue  # Preserve catalog order.
        assigned = min(remaining, max(0, int(quota) - 1))  # Reserve each user's seed cycle.
        if int(allocated_replica) == int(replica_index):  # Return this replica's exact share.
            return assigned  # Front-load capacity deterministically.
        remaining -= assigned  # Carry only the unsatisfied floor.
    raise AssertionError(f"formal repeat replica unavailable: {game_id}:{replica_index}")  # Reject stale metadata.


# Reserve each user's seed settlement, then use its exact Repeat share.
def should_schedule_repeat(game_id, local_ordinal, replica_index, allocations, formal=False):
    if game_id not in REPEAT_CONTROL_SELECTORS or not formal:  # Preserve nonformal and unaffected behavior.
        return False  # Leave the cycle on its fresh strategy.
    return 0 < int(local_ordinal) <= formal_repeat_quota(game_id, replica_index, allocations)  # Spend only the assigned local share.


# Remove every earlier Repeat slot from one fresh cycle's strategy rank.
def formal_ordinary_ordinal(game_id, game_ordinal, local_ordinal, replica_index, allocations):
    prior_repeats = 0  # Count completed shares from prior replicas.
    for allocated_game, _game_index, allocated_replica, _quota, _cycle_start in allocations:  # Traverse stable allocation order.
        if allocated_game != game_id:  # Ignore other games.
            continue  # Preserve the requested rank.
        if int(allocated_replica) >= int(replica_index):  # Stop before the current replica.
            break  # Count its local prefix separately.
        prior_repeats += formal_repeat_quota(game_id, allocated_replica, allocations)  # Remove the prior committed share.
    current_prior = min(max(0, int(local_ordinal) - 1), formal_repeat_quota(game_id, replica_index, allocations))  # Count local Repeat slots before this cycle.
    return int(game_ordinal) - prior_repeats - current_prior  # Produce one globally continuous fresh rank.


# Count prior non-quick Keno cycles in one continuous game schedule.
def keno_nonquick_rank(game_ordinal):
    completed_blocks, remainder = divmod(int(game_ordinal), 16)  # Partition two quick and fourteen individual modes.
    return completed_blocks * 14 + max(0, remainder - 2)  # Count only earlier cell-selection modes.


# Resolve one gapless Keno cell slice including every mode-two replacement.
def keno_number_schedule(ordinary_ordinal):
    ordinal = int(ordinary_ordinal)  # Normalize the fresh-cycle rank.
    start = KENO_NUMBER_CLICKS_PER_CYCLE * keno_nonquick_rank(ordinal) + 5 * max(0, (ordinal + 13) // 16)  # Interleave prior replacements.
    replacement = start + KENO_NUMBER_CLICKS_PER_CYCLE if ordinal % 16 == 2 else None  # Append this cycle's five replacements.
    return start, replacement  # Share exact pointer arithmetic with tests.


# Resolve one gapless Sic Bo slice including the first-hundred replacements.
def sic_bo_wager_schedule(ordinary_ordinal):
    ordinal = int(ordinary_ordinal)  # Normalize the fresh-cycle rank.
    start = SIC_BO_WAGER_CLICKS_PER_CYCLE * ordinal + min(max(ordinal, 0), CONTROL_ACTIVATION_FLOOR)  # Interleave prior replacements.
    replacement = start + SIC_BO_WAGER_CLICKS_PER_CYCLE if ordinal < CONTROL_ACTIVATION_FLOOR else None  # Append this cycle's replacement.
    return start, replacement  # Share exact pointer arithmetic with tests.


# Resolve the time-balanced Roulette mode from its continuous game rank.
def roulette_mode_for_ordinal(game_ordinal):
    return "double" if int(game_ordinal) < 551 else "single"  # Split exact capacity 551/536.


# Resolve the time-balanced exact-floor Roulette number schedule.
def roulette_number_schedule(game_ordinal):
    ordinal = int(game_ordinal)  # Normalize once.
    if ordinal < 101: return ordinal % 38, 1  # Leave primary Rebet ownership far below the unchanged seventeen-minute ceiling.
    if ordinal < 191: return (101 + 5 * (ordinal - 101)) % 38, 5  # Preserve the autoplay-heavy second worker's measured cost.
    if ordinal < 281: return (551 + 9 * (ordinal - 191)) % 38, 9  # Spend replica two's higher-margin capacity.
    if ordinal < 371: return (1361 + 9 * (ordinal - 281)) % 38, 9  # Continue the exact gapless double-zero stream.
    if ordinal < 461: return (2171 + 9 * (ordinal - 371)) % 38, 9  # Balance replica four without exceeding its hosted margin.
    if ordinal < 551:  # Finish the exact double-zero floor on replica five.
        relative = ordinal - 461  # Resolve the final double-zero worker's local rank.
        extras = min(relative, 9)  # Place nine required extra clicks only on its first nine cycles.
        return (2981 + 9 * relative + extras) % 38, 10 if relative < 9 else 9  # Complete exactly 3,800 real number activations.
    relative = ordinal - 551  # Resolve single-zero rank.
    return (7 * relative - min(max(relative - 269, 0), 52)) % 37, 6 if 269 <= relative < 321 else 7  # Complete exactly 3,700 activations.


# Resolve the time-balanced exact-floor Roulette special schedule.
def roulette_special_schedule(game_ordinal):
    ordinal = int(game_ordinal)  # Normalize once.
    if ordinal < 101: return (14 * ordinal) % 139, 14  # Pair with one number click so primary Rebet cycles stay below budget.
    if ordinal < 191: return (1414 + 24 * (ordinal - 101)) % 139, 24  # Preserve the autoplay-heavy second worker's measured cost.
    if ordinal < 236: return (3574 + 29 * (ordinal - 191)) % 139, 29  # Place replica two's forty-five required extras first.
    if ordinal < 281: return (4879 + 28 * (ordinal - 236)) % 139, 28  # Complete replica two's balanced share.
    if ordinal < 327: return (6139 + 29 * (ordinal - 281)) % 139, 29  # Place replica three's forty-six required extras first.
    if ordinal < 371: return (7473 + 28 * (ordinal - 327)) % 139, 28  # Complete replica three's balanced share.
    if ordinal < 461: return (8705 + 28 * (ordinal - 371)) % 139, 28  # Spend replica four's measured margin evenly.
    if ordinal < 526: return (11225 + 30 * (ordinal - 461)) % 139, 30  # Place replica five's sixty-five required extras first.
    if ordinal < 551: return (13175 + 29 * (ordinal - 526)) % 139, 29  # Finish exactly 13,900 double-zero activations.
    relative = ordinal - 551  # Resolve single-zero rank.
    extras = min(max(relative - 180, 0), 89) + min(max(relative - 447, 0), 11)  # Place one hundred extras on lower-runtime workers.
    clicks = 26 if 180 <= relative < 269 or 447 <= relative < 458 else 25  # Spend exactly the reviewed per-cycle budget.
    return (25 * relative + extras) % 135, clicks  # Complete 13,500 single-zero activations.


# Move the hundred shared Roulette autoplay sessions off the primary Rebet worker.
def roulette_autoplay_ordinal(game_ordinal):
    ordinal = int(game_ordinal)  # Normalize the continuous rank.
    return ordinal - 101 if 101 <= ordinal <= 200 else CONTROL_ACTIVATION_FLOOR  # Spend exactly ranks101..200.


# Select exactly fifty lower-pressure cycles for a real opposite-mode probe and its serialized scheduled-mode restoration.
def should_probe_roulette_mode(game_ordinal):
    ordinal = int(game_ordinal)  # Normalize the continuous rank once.
    return 202 <= ordinal <= 1084 and (ordinal - 202) % 18 == 0  # Distribute fifty probes outside the primary Rebet affinity range.


# Select exactly one hundred lower-pressure cycles for a serialized real zero-rule transition.
def should_rotate_roulette_zero_rule(game_ordinal):
    ordinal = int(game_ordinal)  # Normalize the continuous rank once.
    return (101 <= ordinal <= 1081 and (ordinal - 101) % 10 == 0) or ordinal == 1086  # Distribute ninety-nine rotations plus one terminal rotation.


# Preserve the first one hundred catalog-nav activations after removing same-mount replay-only cycles.
def same_mount_repeat_navigation_entry(game_id, ordinary_ordinal):
    labels = {"acey_deucey": "Acey-Deucey", "bingo": "Bingo"}  # Bind diagnostics to the exact two reviewed route-local replay games.
    if game_id not in SAME_MOUNT_REPEAT_GAME_IDS:  # Refuse accidental reuse for a game whose navigation plan was not reviewed.
        raise AssertionError(f"unsupported same-mount Repeat game: {game_id}")  # Preserve one bounded schedule diagnostic.
    ordinal = int(ordinary_ordinal)  # Normalize the gapless fresh rank once.
    if not 0 <= ordinal < 987:  # Reject stale allocation arithmetic outside the exact post-replay fresh inventory.
        raise AssertionError(f"invalid {labels[game_id]} ordinary ordinal: {ordinal}")  # Preserve one bounded game-owned diagnostic.
    return "nav" if ordinal < CONTROL_ACTIVATION_FLOOR else "open"  # Produce exact nav=100 and open=887 across 987 fresh cycles.


# Preserve the historical Bingo schedule seam for focused callers and prior evidence.
def bingo_navigation_entry(ordinary_ordinal):
    return same_mount_repeat_navigation_entry("bingo", ordinary_ordinal)  # Delegate without changing exact navigation arithmetic.


# Expose the independently named Acey-Deucey schedule seam for exact worker eighty-five evidence.
def acey_deucey_navigation_entry(ordinary_ordinal):
    return same_mount_repeat_navigation_entry("acey_deucey", ordinary_ordinal)  # Delegate to the reviewed shared route-preservation plan.


# Resolve the honest opportunity budget for mutually exclusive rare decisions.
def reachable_control_opportunities(signature, seen_counts, activated_counts):
    raw = max(int(seen_counts.get(signature, 0)), int(activated_counts.get(signature, 0)))  # Preserve ordinary opportunities.
    for group in MUTUALLY_EXCLUSIVE_CONTROL_GROUPS:  # Apply only explicit decision groups.
        if signature not in group: continue  # Ignore unrelated controls.
        shared = max((int(seen_counts.get(member, 0)) for member in group), default=0)  # Count the shared state once.
        fair = math.ceil(shared / len(group)) if group else 0  # Divide finite opportunity fairly.
        return max(int(activated_counts.get(signature, 0)), fair), "mutually exclusive rare decision-state share"  # Preserve real activations.
    return raw, ""  # Preserve literal ordinary opportunities.


# Recover an exact registered game from a stable shell-navigation signature.
def catalog_navigation_target(raw_signature):
    for prefix in ("button[data-testid=nav-", "button[data-testid=open-"):  # Recognize only public game route controls.
        if raw_signature.startswith(prefix) and raw_signature.endswith("]"):  # Require a complete stable selector.
            game_id = raw_signature[len(prefix):-1]  # Recover the bounded identifier.
            return game_id if game_id in GAME_IDS else None  # Admit only exact catalog membership.
    return None  # Exclude utilities such as settings.


# Classify whether one namespaced signature belongs to the gameplay floor.
def control_eligibility(signature):
    namespace, separator, raw_signature = signature.partition("::")  # Split the harness-owned namespace.
    if not separator or namespace == "unscoped": return False, "missing surface ownership"  # Reject escaped identities.
    if namespace == "auth": return False, "authentication lifecycle control"  # Exclude one-time credentials.
    if namespace == "shell":  # Admit only exact game routes.
        return (True, "catalog navigation control") if catalog_navigation_target(raw_signature) is not None else (False, "non-gameplay shell control")  # Reject settings and utilities.
    if namespace in GAME_IDS: return True, "registered game control"  # Govern every game-owned action.
    return False, "unknown surface ownership"  # Exclude malformed ownership explicitly.


# Identify catalog navigation deliberately outside a focused game selection.
def unselected_catalog_navigation(signature, selected_games):
    if selected_games is None: return False  # Keep direct classification fail closed.
    namespace, separator, raw_signature = signature.partition("::")  # Split ownership once.
    if namespace != "shell" or not separator: return False  # Limit the exception to valid shell controls.
    game_id = catalog_navigation_target(raw_signature)  # Reuse exact membership parsing.
    return game_id is not None and game_id not in selected_games  # Exclude only deliberately omitted registered games.


# Produce mutually exclusive acceptance classifications for every discovered control.
def classify_control_coverage(seen_counts, activated_counts, minimum=CONTROL_ACTIVATION_FLOOR, selected_games=None):
    classifications = {"exercised": {}, "intentionally_unavailable": {}, "failed": {}, "excluded": {}}  # Keep acceptance and diagnostic classes separate.
    signatures = sorted(set(seen_counts).union(activated_counts))  # Classify the complete discovered-and-activated identity set.
    for signature in signatures:  # Assign every identity exactly once.
        seen = int(seen_counts.get(signature, 0))  # Read distinct rendered-state observations.
        activated = int(activated_counts.get(signature, 0))  # Read successful UI dispatches.
        opportunities, opportunity_reason = reachable_control_opportunities(signature, seen_counts, activated_counts)  # Adjust only explicitly governed mutually exclusive rare states.
        eligible, reason = control_eligibility(signature)  # Apply the durable surface policy.
        if unselected_catalog_navigation(signature, selected_games):  # Recognize catalog routes intentionally absent from a focused game run.
            eligible, reason = False, "unselected registered-game navigation outside focused profile"  # Keep the exact out-of-scope reason visible in terminal evidence.
        evidence = {"seen": seen, "activated": activated, "opportunities": opportunities, "reason": reason}  # Preserve bounded numeric evidence.
        if opportunity_reason:  # Keep the exceptional opportunity calculation explicit in terminal evidence.
            evidence["opportunity_reason"] = opportunity_reason  # Prevent a rare-state exception from becoming an unexplained waiver.
        if not eligible:  # Keep non-gameplay lifecycle controls visible without diluting the floor.
            classifications["excluded"][signature] = evidence  # Record the exact exclusion and reason.
        elif activated >= minimum:  # Accept controls that meet the literal requested activation floor.
            classifications["exercised"][signature] = evidence  # Preserve passing coverage evidence.
        elif opportunities < minimum and activated > 0:  # Accept a genuinely rare conditional control only after at least one real UI activation.
            evidence["reason"] = "fewer than minimum reachable opportunities; exercised in sampled conditional states"  # Explain why the literal floor was impossible while preserving actual-use proof.
            classifications["intentionally_unavailable"][signature] = evidence  # Preserve the allowed conditional classification.
        else:  # Fail controls that were skipped, partially exercised, or ordinarily reachable below the floor.
            evidence["shortfall"] = max(0, minimum - activated)  # Quantify the exact remaining activation deficit.
            classifications["failed"][signature] = evidence  # Keep red evidence actionable.
    classifications["classified_count"] = len(signatures)  # Prove complete classification accounting.
    classifications["eligible_count"] = sum(len(classifications[name]) for name in ("exercised", "intentionally_unavailable", "failed"))  # Count all eligible signatures once.
    return classifications  # Return deterministic machine-readable coverage evidence.
