#!/usr/bin/env python3
# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Run TEST-042/TEST-047/TEST-092 real-browser UI cycles across every catalog game."""

import argparse  # Parse total-cycle, parallelism, timeout, and artifact options.
import asyncio  # Coordinate bounded independent game shards and browser actions.
import json  # Persist sanitized per-shard and aggregate qualification evidence.
import math  # Calculate deterministic nearest-rank latency percentiles.
import os  # Resolve the disposable runtime parent and process-scoped run identity.
import shutil  # Copy and remove isolated runtime trees.
import subprocess  # Launch shard-owned loopback servers without an undrained output pipe.
import sys  # Prefer the current checkout when importing Casino modules.
import tempfile  # Resolve a portable disposable-runtime parent on local and hosted workers.
import time  # Measure browser-visible latency and timestamp the run.
import traceback  # Retain local-only diagnostics for unexpected harness failures.
from collections import Counter  # Aggregate control, error, and coverage counts.
from contextvars import ContextVar  # Isolate control namespaces across concurrent browser shards.
from pathlib import Path  # Handle source, report, deployment, and screenshot paths.

# Resolve this clean checkout before importing project-owned packages.
ROOT = Path(__file__).resolve().parents[1]
# Ensure the checked-out branch wins over any globally installed Casino package.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # Put this source snapshot first on the import path.

from casino.config import GAMES  # Discover all registered games from canonical metadata.
from tests.formal_ui_profile import FORMAL_EXECUTION_BUDGET_SECONDS, formal_replica_policy, formal_worker_heartbeat, stop_formal_worker_heartbeat  # Apply exact-run sizing, monitoring, and the fail-closed execution budget.
from tests.long_suites import OPERATIONS_SMOKE_BUILD_SHA, ApiClient, clear_readonly_and_retry, free_port, stop_server  # Reuse governed API and exact cleanup controls.

# Preserve catalog order for deterministic game quotas and global cycle IDs.
GAME_IDS = tuple(game["id"] for game in GAMES)
# Read module-owned ready selectors so catalog additions cannot silently skip readiness.
READY_TEST_IDS = {game["id"]: game["frontend"]["ready_testid"] for game in GAMES}
# Bind every registered game to one explicit rendered-control strategy family. (TEST-092, issue #1050)
UI_STRATEGY_FAMILIES = {
    "roulette": "roulette",  # Exercise the full table, drawer, refund, and wheel lifecycle.
    "slots": "slots",  # Exercise the cabinet spin lifecycle.
    "keno": "keno",  # Exercise ticket construction, purchase, draw, and reset.
    "bingo": "bingo",  # Exercise card purchase, call, and bounded reset.
    "blackjack": "blackjack",  # Exercise deals and every legal decision state.
    "baccarat": "baccarat",  # Exercise wager placement, refund, and coup settlement.
    "multi_hand_video_poker": "draw_poker",  # Share the five-position hold-and-draw strategy.
    "casino_war": "casino_war",  # Exercise deal and mutually exclusive tie decisions.
    "big_six_wheel": "wager_inputs",  # Share the visible wager-input terminal strategy.
    "dragon_tiger": "dragon_tiger",  # Exercise rotating table bets and deal settlement.
    "red_dog": "red_dog",  # Exercise deal and spread decisions.
    "hi_lo": "hi_lo",  # Exercise both prediction controls.
    "scratch_cards": "scratch_cards",  # Exercise purchase, cell reveal, and reveal-all settlement.
    "sic_bo": "sic_bo",  # Exercise the complete wager board and shake settlement.
    "chuck_a_luck": "wager_inputs",  # Share the visible wager-input terminal strategy.
    "craps": "craps",  # Exercise a complete Pass Line round.
    "jacks_or_better_video_poker": "draw_poker",  # Share the five-position hold-and-draw strategy.
    "deuces_wild_video_poker": "draw_poker",  # Share the five-position hold-and-draw strategy.
    "three_card_poker": "three_card_poker",  # Exercise deal plus Play and Fold.
    "texas_holdem_practice_table": "texas_holdem",  # Exercise fold and call-through practice hands.
    "crown_and_anchor": "wager_inputs",  # Share the visible wager-input terminal strategy.
    "over_under_7": "wager_inputs",  # Share the visible wager-input terminal strategy.
    "plinko": "plinko",  # Exercise one terminal drop.
    "fan_tan": "wager_inputs",  # Share the visible wager-input terminal strategy.
    "andar_bahar": "andar_bahar",  # Exercise both table sides.
    "acey_deucey": "acey_deucey",  # Exercise rendered Pass, Play, and free-boundary states.
    "caribbean_stud": "caribbean_stud",  # Exercise deal plus Call and Fold.
    "let_it_ride": "let_it_ride",  # Exercise both decisions at both stages.
    "casino_holdem": "casino_holdem",  # Exercise deal plus Call and Fold.
    "joker_poker": "draw_poker",  # Share the five-position hold-and-draw strategy.
    "color_wheel": "simple_terminal",  # Share rotating choices, chips, repeat, and terminal action.
    "pai_gow_poker": "pai_gow_poker",  # Exercise manual setting, house way, repeat, and settlement.
    "poker_dice": "simple_terminal",  # Share rotating chips, repeat, and terminal action.
    "boule": "simple_terminal",  # Share rotating number/even-money choices and terminal action.
    "faro": "simple_terminal",  # Share rotating rank/chip choices and terminal action.
    "trente_et_quarante": "simple_terminal",  # Share rotating table/chip choices and terminal action.
    "pachinko": "simple_terminal",  # Share rotating chips, repeat, and terminal action.
    "coin_pusher": "simple_terminal",  # Share rotating chips, repeat, and terminal action.
    "marble_race": "simple_terminal",  # Share rotating market, marble, chip, and terminal action.
    "pattern_draw": "simple_terminal",  # Share rotating pattern/chip choices and terminal action.
    "lucky_grid": "lucky_grid",  # Exercise every cell through complete three-pick reveals.
    "daily_draw_lab": "daily_draw_lab",  # Exercise every number through complete five-pick draws.
    "four_card_poker": "four_card_poker",  # Exercise deal, repeat, fold, and every Play multiplier.
    "double_bonus_video_poker": "draw_poker",  # Reuse the established draw-poker family without duplication.
    "mississippi_stud": "mississippi_stud",  # Exercise repeat and balanced decisions through every street.
    "teen_patti": "teen_patti",  # Exercise deal, repeat, Play, and Fold.
}
# Enumerate every implemented dispatch family so registry entries cannot name a silent no-op.
IMPLEMENTED_UI_STRATEGY_FAMILIES = frozenset({
    "acey_deucey", "andar_bahar", "baccarat", "bingo", "blackjack", "caribbean_stud", "casino_holdem", "casino_war", "craps", "daily_draw_lab", "dragon_tiger", "draw_poker", "four_card_poker", "hi_lo", "keno", "let_it_ride", "lucky_grid", "mississippi_stud", "pai_gow_poker", "plinko", "red_dog", "roulette", "scratch_cards", "sic_bo", "simple_terminal", "slots", "teen_patti", "texas_holdem", "three_card_poker", "wager_inputs",
})
# Rank visible Pai Gow cards from weakest through strongest while keeping the semi-wild Joker out of the low hand.
PAI_GOW_RANK_VALUES = {rank: value for value, rank in enumerate(("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"), start=2)}
# Describe the simple settled-action surfaces without weakening their rendered-control coverage.
SIMPLE_TERMINAL_UI_STRATEGIES = {
    "color_wheel": {"control_groups": (("[data-color]", 1), ("[data-chip]", 1)), "action": '[data-testid="color-wheel-spin"]', "repeat": '[data-testid="color-wheel-repeat"]'},  # Rotate every color and chip before spinning.
    "poker_dice": {"control_groups": (("[data-chip]", 1),), "action": '[data-testid="poker-dice-roll"]', "repeat": '[data-testid="poker-dice-repeat"]'},  # Rotate chips before rolling.
    "boule": {"control_groups": (("[data-bet],[data-number]", 2), ("[data-chip]", 1)), "action": '[data-testid="boule-spin"]', "repeat": '[data-action="repeat"]'},  # Touch two of fourteen wager choices per cycle so every identity exceeds the floor.
    "faro": {"control_groups": (("[data-rank]", 2), ("[data-chip]", 1)), "action": '[data-testid="faro-deal"]', "repeat": '[data-testid="faro-repeat"]'},  # Touch two ranks per cycle so all thirteen exceed the floor.
    "trente_et_quarante": {"control_groups": (("[data-bet]", 1), ("[data-chip]", 1)), "action": '[data-testid="teq-deal"]', "repeat": '[data-action="repeat"]'},  # Rotate all four table choices and chips before dealing.
    "pachinko": {"control_groups": (("[data-chip]", 1),), "action": '[data-testid="pachinko-drop"]', "repeat": '[data-testid="pachinko-repeat"]'},  # Rotate chips before dropping.
    "coin_pusher": {"control_groups": (("[data-chip]", 1),), "action": '[data-testid="coin-pusher-drop"]', "repeat": '[data-testid="coin-pusher-repeat"]'},  # Rotate chips before dropping.
    "marble_race": {"control_groups": (("[data-bet]", 1), ("[data-marble]", 1), ("[data-chip]", 1)), "action": '[data-testid="marble-race-go"]', "repeat": '[data-testid="marble-race-repeat"]'},  # Rotate market, runner, and chip before racing.
    "pattern_draw": {"control_groups": (("[data-bet]", 1), ("[data-chip]", 1)), "action": '[data-testid="pattern-draw-draw"]', "repeat": '[data-testid="pattern-draw-repeat"]'},  # Rotate pattern and chip before drawing.
}
# Apply the authoritative governed viewport inventory to distributed visual evidence.
VIEWPORTS = (
    {"id": "desktop_primary", "width": 1920, "height": 1080},
    {"id": "desktop_compact", "width": 1440, "height": 900},
    {"id": "tablet", "width": 1024, "height": 900},
    {"id": "mobile", "width": 390, "height": 844},
)
# Bound ordinary UI actions tightly enough for a long failure-tolerant qualification.
ACTION_TIMEOUT_MS = 15_000
# Give initial page, authentication, and module loads more room than repeated cycles.
SETUP_TIMEOUT_MS = 20_000
# Require the issue-owned activation floor for every ordinarily reachable eligible control.
CONTROL_ACTIVATION_FLOOR = 100
# Model controls that share one rare decision state where activating one necessarily removes every alternative.
MUTUALLY_EXCLUSIVE_CONTROL_GROUPS = (
    frozenset(("casino_war::button[data-action=surrender]", "casino_war::button[data-action=war]")),
)
# Map shared autoplay games to a visible post-atomic-action readiness control.
AUTOPLAY_SETTLED_SELECTORS = {
    "roulette": ['[data-testid="roulette-spin"]'],  # Require the wheel to accept the next manual spin.
    "slots": ['[data-testid="slots-spin"]'],  # Require the cabinet to accept the next manual spin.
    "keno": ['[data-testid="keno-new-ticket"]', "#quick5"],  # Require result replay or fresh selection readiness.
    "bingo": ['[data-testid="bingo-buy"]', '[data-testid="bingo-call"]', '[data-testid="bingo-reset"]'],  # Require a stable session action.
    "baccarat": ['[data-testid="baccarat-deal"]'],  # Require the card reveal and settlement theater to finish.
}
# Keep every shard and aggregate artifact mapped to the same permanent requirements.
REQUIREMENT_IDS = ("AUTH-001", "AUTH-002", "SESSION-001", "SESSION-005", "TEST-042", "TEST-047", "TEST-092", "CORE-021")
# Register essential non-control stage geometry that human evidence must show completely.
ESSENTIAL_STAGE_CONTRACTS = {
    "big_six_wheel": {"stage": ".big-six-wheel__stage", "contained_items": (".big-six-wheel__wheel-shell", ".big-six-wheel__pointer", ".big-six-wheel__hub"), "paint_items": {".big-six-wheel__wheel": ".big-six-wheel__wheel-shell"}, "paint_min_ratio": 0.8},  # Contain stable theater geometry while requiring the rotating square wheel to paint materially across its circular clipping owner.
    "crown_and_anchor": {"stage": ".crown-anchor__stage", "contained_items": ('[data-die="0"]', '[data-die="1"]', '[data-die="2"]', '[data-symbol="crown"]', '[data-symbol="anchor"]', '[data-symbol="heart"]', '[data-symbol="diamond"]', '[data-symbol="club"]', '[data-symbol="spade"]'), "paint_items": {}, "paint_min_ratio": 0.0},  # Require all three dice and all six hit-result panels to paint fully inside the route-owned stage at every governed viewport.
}
# Keep each asynchronous shard's control identities scoped to auth, shell, or one game.
CONTROL_NAMESPACE = ContextVar("ui_50000_control_namespace", default="unscoped")
# Allow an explicitly governed caller to replace ordinary per-operation timeouts with one task-local absolute deadline.
FORMAL_OPERATION_DEADLINE = ContextVar("ui_50000_formal_operation_deadline", default=None)


# Resolve the explicit rendered-control strategy family for one registered game. (TEST-092)
def strategy_family_for(game_id):
    family = UI_STRATEGY_FAMILIES.get(game_id)  # Read the catalog-bound strategy registration without inferring from markup.
    if family is None:  # Reject every future catalog game until a real strategy is deliberately registered.
        raise AssertionError(f"no UI cycle strategy for catalog game {game_id}")  # Preserve the exact fail-closed catalog diagnostic.
    if family not in IMPLEMENTED_UI_STRATEGY_FAMILIES:  # Reject a registry entry that names no executable dispatch family.
        raise AssertionError(f"no UI cycle strategy implementation for family {family}")  # Keep configuration typos from becoming silent skips.
    return family  # Return only a known implemented family.


# Convert one exception into a bounded single-line local diagnostic.
def safe_error(exc):
    message = str(exc).replace("\r", " ").replace("\n", " ").strip()  # Collapse multiline browser call logs.
    home = str(Path.home())  # Resolve the current private host profile prefix once.
    message = message.replace(home.replace("\\", "\\\\"), "<user-home>").replace(home, "<user-home>")  # Remove literal and escaped private profile prefixes.
    return (message or exc.__class__.__name__)[:500]  # Bound artifacts while preserving the actionable prefix.


# Reauthenticate the long-idle Admin evidence client before one post-soak privileged read. (TEST-092)
def call_post_soak_admin_evidence(client, path):
    client.login_default_user()  # Obtain a fresh session through the public login endpoint after the governed Admin idle window.
    return client.call(path)  # Execute the requested evidence read only with the newly issued bearer session.


# Resolve one ordinary timeout or the remaining task-local formal absolute window.
def operation_timeout_ms(default_timeout_ms):
    deadline = FORMAL_OPERATION_DEADLINE.get()  # Read only the current asynchronous task's optional formal deadline.
    if deadline is None:  # Preserve every ordinary browser profile's established timeout behavior.
        return int(default_timeout_ms)  # Return the caller-owned ordinary timeout unchanged.
    remaining_ms = int((float(deadline) - time.perf_counter()) * 1000)  # Convert the absolute monotonic deadline to a remaining Playwright timeout.
    if remaining_ms < 1:  # Refuse an operation after the formal absolute window has already expired.
        raise TimeoutError("formal gameplay absolute deadline exceeded")  # Keep the terminal diagnostic fixed and identity-free.
    return remaining_ms  # Give the current operation only the remaining formal window, never a fresh per-operation budget.


# Return one nearest-rank percentile from a numeric sample.
def percentile(values, percent):
    if not values:  # Keep missing latency samples explicit.
        return None  # Avoid fabricating a zero-second result.
    ordered = sorted(float(value) for value in values)  # Sort a defensive numeric copy.
    rank = max(0, min(len(ordered) - 1, math.ceil((percent / 100) * len(ordered)) - 1))  # Clamp the nearest-rank index.
    return round(ordered[rank], 4)  # Preserve useful local timing precision.


# Summarize one latency sample for the terminal report.
def latency_summary(values):
    return {  # Return compact count and tail evidence.
        "count": len(values),  # Record the number of measured successful cycles.
        "p50_seconds": percentile(values, 50),  # Record median latency.
        "p95_seconds": percentile(values, 95),  # Record common tail latency.
        "p99_seconds": percentile(values, 99),  # Record near-worst latency.
        "max_seconds": round(max(values), 4) if values else None,  # Record the observed maximum.
    }


# Resolve the immutable source commit so reports from another checkout cannot be resumed.
def resolve_source_commit(repo_root=ROOT):
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_root), capture_output=True, text=True, timeout=10, check=False)  # Ask Git for this checkout's exact commit without modifying it.
    commit = completed.stdout.strip().lower()  # Normalize the public hexadecimal identity.
    if completed.returncode != 0 or len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):  # Reject missing, abbreviated, or malformed provenance.
        raise RuntimeError("unable to resolve exact source commit")  # Fail before starting any browser or listener.
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=str(repo_root), capture_output=True, text=True, timeout=10, check=False)  # Verify the runtime copy will match the recorded commit byte-for-byte.
    if status.returncode != 0 or status.stdout.strip():  # Reject tracked or untracked source drift while ignoring repository-defined evidence paths.
        raise RuntimeError("source checkout must be clean before qualification")  # Prevent a dirty harness or application from claiming committed provenance.
    return commit  # Return the immutable full source identity.


# Validate the immutable source supplied by a distributed aggregate without rejecting downloaded artifacts.
def resolve_distributed_source_commit(expected_commit, repo_root=ROOT):
    commit = str(expected_commit).strip().lower()  # Normalize the workflow-provided full commit identity.
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):  # Reject abbreviated or malformed provenance.
        raise RuntimeError("--source-commit must be one full hexadecimal commit")  # Fail before accepting any downloaded shard.
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_root), capture_output=True, text=True, timeout=10, check=False)  # Read the aggregate checkout identity without modifying it.
    checkout_commit = completed.stdout.strip().lower()  # Normalize the checked-out commit.
    if completed.returncode != 0 or checkout_commit != commit:  # Require the aggregator to run the same exact source as every worker.
        raise RuntimeError("aggregate checkout does not match --source-commit")  # Reject stale or foreign workflow artifacts.
    return commit  # Return the exact distributed identity while permitting downloaded evidence files.


# Prefix one rendered-control signature with its owning surface to prevent cross-game collisions.
def qualify_control_signature(signature, namespace=None):
    owner = namespace or CONTROL_NAMESPACE.get()  # Read the task-local surface unless a unit test supplies one explicitly.
    return f"{owner}::{signature}"  # Preserve the raw selector while adding stable module ownership.


# Keep replicated game schedules continuous while preserving each ordinary game's local coverage budget.
def coverage_ordinal(game_id, local_ordinal, global_cycle):
    return global_cycle if game_id == "roulette" else local_ordinal  # Avoid restarting Roulette's round-robin target schedule in every replica.


# Keep real Rebet attempts on the first Roulette shard until its literal activation floor is satisfied.
def should_exercise_roulette_rebet(replica_index, activated_counts):
    signature = qualify_control_signature("button#rebet", "roulette")  # Resolve the aggregate identity independently of the current context variable.
    return replica_index == 0 and int(activated_counts.get(signature, 0)) < CONTROL_ACTIVATION_FLOOR  # Retry only the primary shard and stop immediately after one hundred real activations.


# Resolve the honest per-control opportunity budget for mutually exclusive rare decision groups.
def reachable_control_opportunities(signature, seen_counts, activated_counts):
    raw_opportunities = max(int(seen_counts.get(signature, 0)), int(activated_counts.get(signature, 0)))  # Preserve the ordinary rendered opportunity count.
    for group in MUTUALLY_EXCLUSIVE_CONTROL_GROUPS:  # Apply only explicitly governed decision-state groups.
        if signature not in group:  # Ignore unrelated controls without weakening their literal floor.
            continue
        shared_states = max((int(seen_counts.get(member, 0)) for member in group), default=0)  # Count each shared decision state once instead of once per alternative.
        fair_share = math.ceil(shared_states / len(group)) if group else 0  # Divide the finite state budget across alternatives that cannot both be activated.
        return max(int(activated_counts.get(signature, 0)), fair_share), "mutually exclusive rare decision-state share"  # Never report fewer opportunities than real activations.
    return raw_opportunities, ""  # Preserve the literal opportunity count for every ordinary control.


# Classify whether one namespaced signature belongs to the #227 gameplay/navigation floor.
def control_eligibility(signature):
    namespace, separator, raw_signature = signature.partition("::")  # Split only the harness-owned namespace prefix.
    if not separator or namespace == "unscoped":  # Reject identities that escaped surface ownership.
        return False, "missing surface ownership"  # Keep malformed evidence explicit and excluded.
    if namespace == "auth":  # Keep credential and terms controls outside repeated gameplay counts.
        return False, "authentication lifecycle control"  # Record why login is exercised once per isolated shard.
    if namespace == "shell":  # Admit only the visible game-routing controls from the persistent shell.
        eligible_navigation = raw_signature.startswith("button[data-testid=nav-") or raw_signature.startswith("button[data-testid=open-")  # Recognize dynamic catalog navigation identities.
        return (True, "catalog navigation control") if eligible_navigation else (False, "non-gameplay shell control")  # Classify settings, logout, and utility controls explicitly.
    if namespace in GAME_IDS:  # Treat every rendered actionable control inside a registered game root as eligible.
        return True, "registered game control"  # Require coverage or evidence for the module-owned control.
    return False, "unknown surface ownership"  # Exclude only with an explicit malformed/unknown reason.


# Identify catalog navigation that is deliberately outside a focused game selection.
def unselected_catalog_navigation(signature, selected_games):
    if selected_games is None:  # Preserve the historical fail-closed policy when no explicit test scope is supplied.
        return False  # Keep default and direct classifier callers strict.
    namespace, separator, raw_signature = signature.partition("::")  # Split the harness-owned surface namespace once.
    if namespace != "shell" or not separator:  # Limit this exception to valid persistent-shell identities.
        return False  # Never exempt game-owned, authentication, malformed, or unscoped controls.
    for prefix in ("button[data-testid=nav-", "button[data-testid=open-"):  # Recognize only the two governed catalog routing identities.
        if raw_signature.startswith(prefix) and raw_signature.endswith("]"):  # Require the complete selector shape emitted by the harness.
            game_id = raw_signature[len(prefix):-1]  # Recover the exact registered game identifier from the selector.
            return game_id in GAME_IDS and game_id not in selected_games  # Exclude only registered games deliberately omitted from this focused profile.
    return False  # Keep every other shell identity on its ordinary eligibility path.


# Produce mutually exclusive acceptance classifications for every discovered or activated control.
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


# Start one disposable loopback server without a finite stdout pipe that could stall a 50,000-cycle run.
def start_ui_server(repo_root):
    port = free_port()  # Allocate one non-reserved loopback port through the governed helper.
    child_environment = {**os.environ, "CASINO_BUILD_SHA": OPERATIONS_SMOKE_BUILD_SHA}  # Publish sanitized test provenance to the disposable runtime.
    command = [sys.executable, str(repo_root / "run.py"), "--host", "127.0.0.1", "--port", str(port), "--no-browser"]  # Bind only the tracked local test server.
    proc = subprocess.Popen(command, cwd=str(repo_root), env=child_environment, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)  # Discard verbose request logs so their pipe cannot block the server.
    client = ApiClient(f"http://127.0.0.1:{port}")  # Build the readiness and evidence client for this exact listener.
    for _ in range(200):  # Poll readiness for up to twenty seconds on busy catalog starts.
        try:  # Accept readiness only after public authentication succeeds.
            client.login_default_user()  # Probe the real login endpoint without exposing the credential.
            return proc, client  # Return only the tracked ready process and client.
        except Exception:  # Retry transient startup states within the bounded interval.
            time.sleep(0.1)  # Give the local child a short boot interval.
    stop_server(proc, client)  # Stop and verify closure of only the failed tracked child.
    raise RuntimeError("disposable UI server did not become ready")  # Fail setup without leaking raw server output.


# Resolve a stable selector-like signature from one rendered form control.
async def control_signature(locator):
    expression = """node => { const tag = node.tagName.toLowerCase(); if (node.hasAttribute('data-clear')) return `${tag}[data-clear]`; if (node.hasAttribute('data-remove-bet')) return `${tag}[data-remove-bet]`; const attrs = ['data-testid','data-action','data-decision','data-guess','data-side','data-bet','data-bet-id','data-betid','data-num','data-dozen','data-column','data-outside','data-outbtn','data-call','data-wager','data-chip','data-hand-count','data-coin-count','data-hold-position','data-play','data-spin','data-roll']; for (const attr of attrs) { if (node.hasAttribute(attr)) return `${tag}[${attr}=${node.getAttribute(attr)}]`; } if (node.id) return `${tag}#${node.id}`; const label = node.getAttribute('aria-label') || node.textContent || node.getAttribute('name') || node.type || 'control'; return `${tag}:${label.trim().replace(/\\s+/g,' ').slice(0,80)}`; }"""  # Prefer stable metadata and collapse dynamic ticket ids into semantic remove actions.
    expression = expression.replace("'data-num',", "'data-num','data-number','data-cell','data-color','data-rank','data-marble','data-card-index',")  # Distinguish every newly covered board, choice, runner, rank, and hand-setting control.
    expression = expression.replace("'data-wager',", "'data-wager','data-ante','data-aces',").replace("'data-play',", "'data-play','data-fold','data-deal','data-repeat',")  # Distinguish staged wager, decision, deal, and repeat controls.
    return qualify_control_signature(await locator.evaluate(expression))  # Read DOM metadata and bind it to the task-local surface.


# Inventory visible enabled controls on the current authenticated surface.
async def inventory_controls(page, seen_counts):
    namespace = CONTROL_NAMESPACE.get()  # Read the task-local owning surface.
    root_selector = "#view" if namespace in READY_TEST_IDS else None  # Scan the complete game outlet while excluding persistent shell controls.
    expression = """rootSelector => { const root = rootSelector ? document.querySelector(rootSelector) : document; if (!root) return []; const attrs = ['data-testid','data-action','data-decision','data-guess','data-side','data-bet','data-bet-id','data-betid','data-num','data-dozen','data-column','data-outside','data-outbtn','data-call','data-wager','data-chip','data-hand-count','data-coin-count','data-hold-position','data-play','data-spin','data-roll']; return [...root.querySelectorAll('button,input,select,summary')].filter(node => !node.disabled && node.getClientRects().length && getComputedStyle(node).visibility !== 'hidden' && (node.tagName === 'SUMMARY' || !node.closest('details:not([open])'))).map(node => { const tag = node.tagName.toLowerCase(); if (node.hasAttribute('data-clear')) return `${tag}[data-clear]`; if (node.hasAttribute('data-remove-bet')) return `${tag}[data-remove-bet]`; for (const attr of attrs) { if (node.hasAttribute(attr)) return `${tag}[${attr}=${node.getAttribute(attr)}]`; } if (node.id) return `${tag}#${node.id}`; const label = node.getAttribute('aria-label') || node.textContent || node.getAttribute('name') || node.type || 'control'; return `${tag}:${label.trim().replace(/\\s+/g,' ').slice(0,80)}`; }); }"""  # Discover only semantically visible enabled controls within the owned game root or current shell/auth surface.
    expression = expression.replace("'data-num',", "'data-num','data-number','data-cell','data-color','data-rank','data-marble','data-card-index',")  # Keep inventory identities aligned with the newly covered board and setting controls.
    expression = expression.replace("'data-wager',", "'data-wager','data-ante','data-aces',").replace("'data-play',", "'data-play','data-fold','data-deal','data-repeat',")  # Keep staged input and decision identities aligned with pointer accounting.
    for signature in await page.evaluate(expression, root_selector):  # Visit every stable signature on this owned UI state.
        seen_counts[qualify_control_signature(signature, namespace)] += 1  # Count namespaced observations for later classification.


# Return whether a locator currently resolves to one visible enabled control.
async def locator_ready(locator):
    return bool(await locator.count() and await locator.first.is_visible() and await locator.first.is_enabled())  # Require real actionability.


# Wait until any selector in caller priority order becomes visible and enabled.
async def wait_any_enabled(page, selectors, timeout_ms=ACTION_TIMEOUT_MS):
    expression = """selectors => selectors.some(selector => { const node = document.querySelector(selector); return Boolean(node && !node.disabled && node.getClientRects().length); })"""  # Poll rendered actionability without clicking.
    try:  # Add the bounded selector intent to otherwise generic Playwright timeout evidence.
        await page.wait_for_function(expression, arg=selectors, timeout=operation_timeout_ms(timeout_ms))  # Wait through asynchronous rerenders without resetting a formal absolute deadline.
    except Exception as exc:  # Convert framework-only timeouts into actionable control-state evidence.
        raise AssertionError(f"enabled control timeout: {selectors}") from exc  # Preserve only public selector identities.
    for selector in selectors:  # Preserve caller priority when several actions are ready.
        locator = page.locator(selector).first  # Re-resolve against the current DOM.
        if await locator_ready(locator):  # Require one visible enabled target.
            return selector  # Return the actionable selector.
    raise AssertionError(f"enabled control disappeared: {selectors}")  # Fail a racy state transition explicitly.


# Wait until Roulette's asynchronous wager drawer publishes one exact committed row count.
async def wait_roulette_bet_drawer(page, expected_rows, timeout_ms=ACTION_TIMEOUT_MS):
    expression = """expected => { const clear = document.querySelector('#clear'); const rows = [...document.querySelectorAll('[data-clear]')]; if (!clear || rows.length !== expected) return false; if (expected === 0) return clear.disabled; return !clear.disabled && rows.every(row => !row.disabled && row.getClientRects().length); }"""  # Bind acceptance to both the clear-all state and every rendered removable wager row.
    try:  # Convert a missing request-owned rerender into one bounded harness diagnostic.
        await page.wait_for_function(expression, arg=int(expected_rows), timeout=operation_timeout_ms(timeout_ms))  # Wait through the asynchronous refund or wager response before another mutation.
    except Exception as exc:  # Preserve only the public drawer-state contract in terminal evidence.
        raise AssertionError(f"Roulette bet drawer did not settle at {expected_rows} rows") from exc  # Reject overlapping wager mutations instead of clicking a stale DOM instance.


# Wait until a Roulette wager response publishes at least one requested number of committed drawer rows.
async def wait_roulette_bet_drawer_minimum(page, minimum_rows, timeout_ms=ACTION_TIMEOUT_MS):
    expression = """minimum => { const clear = document.querySelector('#clear'); const rows = [...document.querySelectorAll('[data-clear]')]; return Boolean(clear && !clear.disabled && rows.length >= minimum && rows.every(row => !row.disabled && row.getClientRects().length)); }"""  # Accept single bets and multi-component call bets only after their complete response-owned render.
    try:  # Convert a missing populated rerender into one bounded harness diagnostic.
        await page.wait_for_function(expression, arg=int(minimum_rows), timeout=operation_timeout_ms(timeout_ms))  # Wait until the wager response exposes its removable drawer rows.
    except Exception as exc:  # Preserve only the public populated-drawer contract in terminal evidence.
        raise AssertionError(f"Roulette bet drawer did not reach {minimum_rows} rows") from exc  # Reject a wager mutation that never became player-visible.


# Add one Roulette wager and wait until its request-owned drawer rerender commits.
async def roulette_add_bet(page, locator, activated_counts):
    rows_before = await page.locator("[data-clear]").count()  # Capture the current committed drawer size before dispatching a new wager.
    await click_locator(locator, activated_counts)  # Activate the rendered table target through Playwright's real pointer path.
    await wait_roulette_bet_drawer_minimum(page, rows_before + 1)  # Serialize single or multi-component wager responses before another mutation can replace their DOM.


# Click a locator through Playwright's real pointer path and record its signature.
async def click_locator(locator, activated_counts, timeout_ms=ACTION_TIMEOUT_MS):
    await locator.wait_for(state="visible", timeout=operation_timeout_ms(timeout_ms))  # Require the control to render within any active formal absolute deadline.
    if not await locator.is_enabled():  # Refuse disabled programmatic activation.
        raise AssertionError("rendered control was disabled")  # Preserve actual UI semantics.
    signature = await control_signature(locator)  # Capture the stable control identity before rerender.
    await locator.click(timeout=operation_timeout_ms(timeout_ms))  # Use a real actionability-checked pointer click without resetting a formal deadline.
    activated_counts[signature] += 1  # Count only successfully dispatched UI activations.
    return signature  # Return the activated signature for state-specific logic.


# Click one selector and record the rendered control signature.
async def click_control(page, selector, activated_counts, timeout_ms=ACTION_TIMEOUT_MS):
    await wait_any_enabled(page, [selector], timeout_ms)  # Wait for the requested public action.
    return await click_locator(page.locator(selector).first, activated_counts, timeout_ms)  # Dispatch through the DOM.


# Fill one rendered input and record it as a control activation.
async def fill_control(locator, value, activated_counts, timeout_ms=ACTION_TIMEOUT_MS):
    await locator.wait_for(state="visible", timeout=operation_timeout_ms(timeout_ms))  # Require the input to render within any active formal absolute deadline.
    if not await locator.is_enabled():  # Respect disabled configuration states.
        raise AssertionError("rendered input was disabled")  # Refuse hidden backdoor changes.
    signature = await control_signature(locator)  # Capture stable input identity.
    await locator.fill(str(value), timeout=operation_timeout_ms(timeout_ms))  # Enter the synthetic value without resetting a formal deadline.
    activated_counts[signature] += 1  # Count the successful UI edit.
    return signature  # Return the input signature for evidence.


# Select one option through the rendered select control and record its stable identity.
async def select_control(locator, value, activated_counts, timeout_ms=ACTION_TIMEOUT_MS):
    await locator.wait_for(state="visible", timeout=operation_timeout_ms(timeout_ms))  # Require the select to render within any active formal absolute deadline.
    if not await locator.is_enabled():  # Respect phase-owned configuration locking.
        raise AssertionError("rendered select was disabled")  # Refuse a hidden programmatic mutation.
    signature = await control_signature(locator)  # Capture identity before a change-triggered rerender.
    await locator.select_option(str(value), timeout=operation_timeout_ms(timeout_ms))  # Change the value without resetting a formal deadline.
    activated_counts[signature] += 1  # Count only a successful rendered selection.
    return signature  # Return the configuration identity for evidence.


# Exercise disclosures plus one rotating visible configuration field without bypassing the UI.
async def exercise_configuration_controls(page, ordinal, activated_counts):
    game_id = CONTROL_NAMESPACE.get()  # Bind discovery to the current registered game surface.
    if game_id not in READY_TEST_IDS:  # Refuse accidental configuration attribution outside a registered game.
        return  # Preserve auth and shell ownership boundaries.
    root = page.locator("#view").first  # Cover the complete game outlet while excluding persistent shell controls.
    summaries = await enabled_locators(root, "summary")  # Discover module-owned disclosure controls.
    for summary in summaries:  # Leave every disclosure open while counting its actual toggle action.
        details_open = await summary.evaluate("node => Boolean(node.parentElement?.open)")  # Read the semantic details state.
        if details_open:  # Exercise an already-open disclosure without changing its terminal state.
            await click_locator(summary, activated_counts)  # Close it through the rendered summary.
            await click_locator(summary, activated_counts)  # Reopen it for nested-control discovery.
        else:  # Open a collapsed disclosure through the real control.
            await click_locator(summary, activated_counts)  # Expose its configuration descendants.
    configurations = await enabled_locators(root, "input:not([type=hidden]),select")  # Discover visible editable controls after disclosures open.
    if not configurations:  # Allow games whose full interaction surface is button-only.
        return  # Preserve the game-specific strategy as the only action path.
    target = configurations[ordinal % len(configurations)]  # Rotate the field budget across every visible configuration identity.
    tag_name = await target.evaluate("node => node.tagName.toLowerCase()")  # Select the correct public interaction for this field type.
    if tag_name == "select":  # Rotate to another enabled option when possible.
        option_values = await target.evaluate("node => [...node.options].filter(option => !option.disabled).map(option => option.value)")  # Read rendered option values only.
        current_value = await target.input_value()  # Preserve the current option for deterministic rotation.
        next_index = (option_values.index(current_value) + 1) % len(option_values) if option_values else 0  # Advance safely through the real option list.
        await select_control(target, option_values[next_index], activated_counts)  # Dispatch the change through the select element.
        return  # Avoid using the now possibly rerendered locator.
    input_type = (await target.get_attribute("type") or "text").lower()  # Resolve checkbox and text-like semantics.
    if input_type in {"checkbox", "radio"}:  # Use a real click for binary configuration controls.
        await click_locator(target, activated_counts)  # Change the rendered binary setting.
        return  # Let the game-specific save action persist it when applicable.
    current_value = await target.input_value()  # Reuse a valid bounded value for text and numeric inputs.
    if not current_value:  # Supply a safe value only when the rendered field is empty.
        current_value = await target.get_attribute("min") or "1"  # Respect a declared minimum before using the neutral fallback.
    await fill_control(target, current_value, activated_counts)  # Exercise the field through real keyboard-style form input.


# Exercise shared autoplay start and stop exactly within the first one hundred assigned cycles.
async def exercise_autoplay_controls(page, ordinal, activated_counts):
    if ordinal >= CONTROL_ACTIVATION_FLOOR:  # Bound control-plane work to the literal requested activation floor.
        return  # Keep the remaining game cycles focused on gameplay distribution.
    game_id = CONTROL_NAMESPACE.get()  # Bind the shared widget lookup to the current module root.
    if game_id not in READY_TEST_IDS:  # Refuse accidental lifecycle work outside a registered game.
        return  # Preserve auth and shell ownership boundaries.
    root = page.locator("#view").first  # Search the complete game outlet while excluding persistent shell controls.
    start = root.locator('[data-testid$="-auto-start"]').first  # Resolve the current game-owned shared Start control.
    if not await locator_ready(start):  # Skip modules that intentionally do not expose shared autoplay.
        return  # Preserve their manual-only contract.
    rounds = root.locator('[data-testid$="-auto-rounds"]').first  # Resolve the shared round-limit input.
    if await locator_ready(rounds):  # Keep the session alive long enough to expose Stop.
        await fill_control(rounds, "1000", activated_counts)  # Enter a bounded synthetic-only high limit through the UI.
    await click_locator(start, activated_counts)  # Start through the same rendered control a player uses.
    stop_selector = '[data-testid$="-auto-stop"]'  # Address the paired module-owned Stop control.
    await wait_any_enabled(page, [stop_selector], SETUP_TIMEOUT_MS)  # Require truthful running state after server registration.
    await click_control(page, stop_selector, activated_counts, SETUP_TIMEOUT_MS)  # Request stop through the rendered control.
    await wait_any_enabled(page, ['[data-testid$="-auto-start"]'], SETUP_TIMEOUT_MS)  # Require the committed atomic action to finish and return idle.
    settled_selectors = AUTOPLAY_SETTLED_SELECTORS.get(game_id)  # Resolve the module's public next-action boundary.
    if settled_selectors:  # Wait beyond the control-plane flag for any already-committed game action.
        await page.wait_for_timeout(75)  # Let the already-started action publish its busy/phase transition before readiness polling.
        await wait_any_enabled(page, settled_selectors, SETUP_TIMEOUT_MS)  # Prevent the manual cycle from racing the final autoplay render.


# Reset Bingo through its rendered control and accept only its active called-session confirmation. (TEST-092, issue #1052)
async def bingo_reset_to_purchase(page, activated_counts):
    call = page.locator('[data-testid="bingo-call"]').first  # Resolve the public active-session signal without reading private game state.
    called_balls = page.locator('[data-testid="bingo-called-ball"]')  # Resolve rendered call history that makes reset destructive.
    requires_confirmation = await locator_ready(call) and await called_balls.count() > 0  # Distinguish active called sessions from completed history still shown on the board.
    accepted_dialog_types = []  # Record the one dialog handled by this exact destructive reset.

    async def accept_reset_confirmation(dialog):
        accepted_dialog_types.append(dialog.type)  # Preserve the public browser-dialog type before accepting it.
        await dialog.accept()  # Confirm the same abandonment prompt a player must accept.

    if requires_confirmation:  # Install a handler only when the rendered state proves reset will prompt.
        page.once("dialog", accept_reset_confirmation)  # Scope confirmation authority to the next dialog from this reset click.
    await click_control(page, '[data-testid="bingo-reset"]', activated_counts)  # Activate the visible Reset control through Playwright's real pointer path.
    if requires_confirmation and accepted_dialog_types != ["confirm"]:  # Require exactly one expected confirmation to have unblocked the click.
        raise AssertionError(f"Bingo reset confirmation mismatch: {accepted_dialog_types}")  # Reject a missing or wrong browser-dialog boundary.
    await wait_any_enabled(page, ['[data-testid="bingo-buy"]'])  # Require authoritative fresh-card readiness after reset.


# Click one terminal action and require it to become ready for another round.
async def terminal_action(page, selector, activated_counts):
    await click_control(page, selector, activated_counts)  # Start the public UI-owned atomic action.
    await page.wait_for_timeout(5)  # Allow the busy-state rerender to replace the control.
    await wait_any_enabled(page, [selector])  # Require terminal next-round readiness.


# Spin Roulette only after observing its explicit resolving transition and later next-round readiness.
async def roulette_terminal_action(page, activated_counts):
    selector = '[data-testid="roulette-spin"]'  # Reuse the public primary-action identity for click and readiness evidence.
    await click_control(page, selector, activated_counts)  # Start the real pointer-owned spin through the rendered control.
    resolving_expression = """() => { const result = document.querySelector('[data-testid=\"roulette-result-region\"]'); const spin = document.querySelector('[data-testid=\"roulette-spin\"]'); return Boolean(result?.dataset.phase === 'spinning' && spin?.disabled); }"""  # Require the committed disabled resolving render before polling for the next round.
    try:  # Convert framework-only timing failures into one stable Roulette transition diagnostic.
        await page.wait_for_function(resolving_expression, timeout=operation_timeout_ms(ACTION_TIMEOUT_MS))  # Prevent the pre-click enabled node from satisfying terminal readiness during its replacement race.
    except Exception as exc:  # Preserve a missing busy transition as an actionable product or harness failure.
        raise AssertionError("Roulette spin did not enter resolving state") from exc  # Expose only the public state contract in terminal evidence.
    await wait_any_enabled(page, [selector])  # Accept the cycle only after settlement returns a genuinely enabled fresh-spin control.


# Remove one contextual wager, clear the drawer, seed one final wager, and spin only after every rerender commits.
async def roulette_reset_seed_and_spin(page, ordinal, activated_counts):
    remove_buttons = await enabled_locators(page, "[data-clear]")  # Discover contextual refund controls only after all preceding wagers have committed.
    if remove_buttons:  # Exercise one semantic removal without assuming the drawer is already empty.
        rows_before = len(remove_buttons)  # Preserve the exact committed row count that owns the selected refund.
        await click_locator(remove_buttons[ordinal % rows_before], activated_counts)  # Remove one rendered wager through the public drawer.
        await wait_roulette_bet_drawer(page, rows_before - 1)  # Require the refund response and replacement DOM before clear-all.
    await click_control(page, "#clear", activated_counts)  # Exercise full bet clearing through the rendered control.
    await wait_roulette_bet_drawer(page, 0)  # Require the empty rerender so no late refund can race the replacement wager.
    replacement_numbers = await enabled_locators(page, '[data-testid^="roulette-num-"]')  # Re-resolve number targets only after clear-all owns the current DOM.
    if not replacement_numbers:  # Require a playable table after clearing.
        raise AssertionError("Roulette number targets unavailable after clear")  # Preserve a broken reset state.
    await roulette_add_bet(page, replacement_numbers[ordinal % len(replacement_numbers)], activated_counts)  # Commit one bounded wager and await its populated drawer.
    await roulette_terminal_action(page, activated_counts)  # Observe the strict disabled resolving render before accepting settlement.


# Complete one Acey-Deucey round without editing its wager before the boundary deal enables that decision input.
async def acey_deucey_terminal_action(page, ordinal, seen_counts, activated_counts):
    await click_control(page, '[data-action="deal"]', activated_counts)  # Reveal the two free boundary cards before touching the phase-owned wager input.
    choice = await wait_any_enabled(page, ['[data-action="play"]', '[data-action="pass"]', '[data-action="deal"]'])  # Wait for a legal decision or an automatically terminal pair/consecutive deal.
    if choice == '[data-action="deal"]':  # Accept a round that settled without exposing a player decision.
        await inventory_controls(page, seen_counts)  # Preserve the terminal next-deal control for complete coverage accounting.
        return "non_wager"  # Classify the automatic free-boundary result without fabricating ledger evidence.
    await inventory_controls(page, seen_counts)  # Discover both legal decision controls and the newly enabled wager input.
    decisions = await enabled_locators(page, '[data-action="play"],[data-action="pass"]')  # Resolve only currently actionable decision buttons after the deal rerender.
    if not decisions:  # Reject a prepared round that exposes no legal choice.
        raise AssertionError("Acey-Deucey exposed no decision")  # Preserve a bounded product-state diagnostic.
    decision = decisions[ordinal % len(decisions)]  # Rotate real Play and Pass actions across the complete game quota.
    action = await decision.get_attribute("data-action")  # Read the stable semantic identity before the decision rerenders the route.
    if action == "play":  # Supply a wager only for the action whose real contract consumes one.
        await fill_control(page.locator("#acey-wager").first, "1", activated_counts)  # Edit the now-enabled public input immediately before Play.
    elif action != "pass":  # Refuse an unexpected control admitted by a future selector regression.
        raise AssertionError("Acey-Deucey exposed an unknown decision")  # Keep the state-machine mismatch actionable.
    await click_locator(decision, activated_counts)  # Commit the selected decision through Playwright's real pointer path.
    await wait_any_enabled(page, ['[data-action="deal"]'])  # Require terminal settlement and fresh-boundary readiness.
    return "wager_required" if action == "play" else "non_wager"  # Bind ledger acceptance to the actual rendered decision.


# Select one least-covered draw-poker hold only after both the deal and hold response own the rendered DOM.
async def draw_poker_select_balanced_hold(page, seen_counts, activated_counts):
    selector = '[data-hold-position][aria-pressed="false"]'  # Address only currently unheld source cards so the pointer action always adds a hold.
    await wait_any_enabled(page, [selector])  # Require the asynchronous deal response to publish the actionable decision state.
    await inventory_controls(page, seen_counts)  # Count all five hold opportunities only after the live hand is committed.
    holds = await enabled_locators(page, selector)  # Re-resolve the five unheld cards from the response-owned DOM.
    positions = [await hold.get_attribute("data-hold-position") for hold in holds]  # Read stable semantic positions before any click rerenders the hand.
    if set(positions) != {"0", "1", "2", "3", "4"}:  # Reject an incomplete or duplicate five-card decision surface.
        raise AssertionError(f"draw-poker hold controls incomplete: {positions}")  # Preserve the exact public position inventory without private state.
    target = await least_activated_locator(holds, activated_counts)  # Balance the literal activation floor across all five stable identities.
    target_position = await target.get_attribute("data-hold-position")  # Bind the post-response wait to the clicked public card identity.
    await click_locator(target, activated_counts)  # Toggle the selected hold through the real pointer and public API path.
    committed_expression = """position => [...document.querySelectorAll('[data-hold-position]')].some(node => node.dataset.holdPosition === String(position) && node.getAttribute('aria-pressed') === 'true' && !node.disabled && node.getClientRects().length)"""  # Require the persisted response to publish the selected, actionable held card.
    try:  # Convert a lost or stale hold response into one bounded state-contract diagnostic.
        await page.wait_for_function(committed_expression, arg=target_position, timeout=operation_timeout_ms(ACTION_TIMEOUT_MS))  # Serialize the hold mutation before Draw can consume its server-owned state.
    except Exception as exc:  # Preserve only the public rendered-state failure in terminal evidence.
        raise AssertionError(f"draw-poker hold did not commit at position {target_position}") from exc  # Reject a draw that would race or omit the selected hold.


# Choose the two weakest visible distinct ranks so the remaining five-card Pai Gow high hand stays legally stronger.
def pai_gow_low_hand_positions(card_ranks):
    ranked = sorted(enumerate(card_ranks), key=lambda item: (PAI_GOW_RANK_VALUES.get(str(item[1]).upper(), 99), item[0]))  # Sort visible ordinary ranks first and the Joker/unknown marker last.
    if len(ranked) < 2:  # Reject an incomplete public seven-card setting surface.
        raise AssertionError(f"Pai Gow setting exposed {len(ranked)} card ranks")  # Preserve only the bounded rendered count.
    first_position, first_rank = ranked[0]  # Assign the weakest visible card to the low hand.
    second = next((item for item in ranked[1:] if str(item[1]).upper() != str(first_rank).upper()), ranked[1])  # Prefer a distinct rank so the low hand cannot become a pair above a high-card high hand.
    return first_position, second[0]  # Return stable rendered positions for real pointer activation.


# Read visible Pai Gow rank glyphs and derive one legal manual low-hand selection.
async def pai_gow_visible_low_hand_positions(page):
    cards = page.locator("[data-card-index]")  # Resolve the seven rendered setting buttons in stable position order.
    ranks = []  # Preserve only public rank glyphs, never hidden dealer or server state.
    for index in range(await cards.count()):  # Inspect every player card tile once.
        rank_node = cards.nth(index).locator(".playing-card__rank")  # Resolve the shared visible rank primitive inside this tile.
        ranks.append((await rank_node.text_content()).strip() if await rank_node.count() else "JOKER")  # Keep a semi-wild Joker out of the low-hand preference.
    return pai_gow_low_hand_positions(ranks)  # Apply the deterministic legal visible-rank policy.


# Return all visible enabled locators matching a selector after a decision rerender.
async def enabled_locators(page, selector):
    ready = []  # Preserve DOM order for deterministic cycling.
    locator = page.locator(selector)  # Resolve the candidate collection.
    for index in range(await locator.count()):  # Inspect each currently rendered candidate.
        item = locator.nth(index)  # Bind one stable indexed locator.
        if await item.is_visible() and await item.is_enabled():  # Retain only real actions.
            ready.append(item)  # Add the actionable locator.
    return ready  # Return the current decision set.


# Choose the currently enabled control with the largest remaining activation deficit.
async def least_activated_locator(locators, activated_counts):
    scored = []  # Preserve DOM order as the deterministic tie breaker.
    for index, locator in enumerate(locators):  # Inspect only the caller's already actionability-filtered controls.
        signature = await control_signature(locator)  # Resolve the same stable identity used by aggregate accounting.
        scored.append((int(activated_counts.get(signature, 0)), index, locator))  # Prioritize the least-used signature, then its rendered order.
    if not scored:  # Refuse an empty decision set explicitly.
        raise AssertionError("no enabled control available for deficit selection")  # Preserve one bounded harness diagnostic.
    return min(scored, key=lambda item: (item[0], item[1]))[2]  # Return the real rendered locator without programmatic activation.


# Activate a rotating semantic control group, re-resolving after every module rerender.
async def rotate_control_group(page, selector, ordinal, clicks_per_cycle, activated_counts):
    for offset in range(clicks_per_cycle):  # Spend the configured honest pointer budget across this group.
        controls = await enabled_locators(page, selector)  # Re-resolve the current DOM after any prior selection repaint.
        if not controls:  # Reject a configured group that is absent or disabled.
            raise AssertionError(f"UI strategy control group unavailable: {selector}")  # Preserve one bounded public-selector diagnostic.
        target_index = (ordinal * clicks_per_cycle + offset) % len(controls)  # Continue a deterministic even rotation across cycles.
        await click_locator(controls[target_index], activated_counts)  # Activate only the real rendered target.


# Exercise an enabled one-click repeat as the complete terminal play for the first hundred reachable cycles.
async def maybe_repeat_terminal(page, ordinal, repeat_selector, ready_selector, activated_counts):
    if not 0 < ordinal <= CONTROL_ACTIVATION_FLOOR:  # Reserve exactly one hundred post-bootstrap cycles for repeat coverage.
        return False  # Leave the ordinary configured play path unchanged outside the coverage window.
    repeat = page.locator(repeat_selector).first  # Resolve the current route's repeat control.
    if not await locator_ready(repeat):  # Permit the first mounted cycle to establish replay state.
        return False  # Fall back to one ordinary play when no replay is legitimately available.
    await click_locator(repeat, activated_counts)  # Replay the last committed wager through the real pointer control.
    await page.wait_for_timeout(5)  # Allow the busy-state rerender to replace the control before polling readiness.
    await wait_any_enabled(page, [ready_selector])  # Require terminal next-round readiness after the repeated settlement.
    return True  # Report that this cycle already completed one terminal play.


# Exercise one simple configured-choice game through repeat or a fresh terminal action.
async def play_simple_terminal_game(page, game_id, ordinal, activated_counts):
    strategy = SIMPLE_TERMINAL_UI_STRATEGIES[game_id]  # Resolve the catalog-audited selectors for this explicit family member.
    if await maybe_repeat_terminal(page, ordinal, strategy["repeat"], strategy["action"], activated_counts):  # Close the repeat deficit without adding a second wager.
        return  # Preserve exactly one terminal settlement for this UI cycle.
    for selector, clicks_per_cycle in strategy["control_groups"]:  # Exercise every configured ready-state choice family.
        await rotate_control_group(page, selector, ordinal, clicks_per_cycle, activated_counts)  # Rotate real pointer coverage evenly.
    await terminal_action(page, strategy["action"], activated_counts)  # Commit and observe one complete fresh round.


# Fill exactly one rotating wager input and clear other compatible wager fields.
async def rotate_wager_inputs(page, ordinal, activated_counts):
    inputs = page.locator("[data-wager]")  # Discover module-owned outcome inputs.
    count = await inputs.count()  # Count selectable wager outcomes.
    if count < 1:  # Refuse silent zero-control coverage.
        raise AssertionError("no rendered wager inputs")  # Preserve the missing-control defect.
    for index in range(count):  # Clear all persisted outcome values before this play.
        item = inputs.nth(index)  # Bind one current input.
        if await item.is_visible() and await item.is_enabled():  # Edit only actionable inputs.
            await fill_control(item, "0", activated_counts)  # Remove the previous wager through the UI.
    target = inputs.nth(ordinal % count)  # Rotate coverage across every rendered outcome.
    await fill_control(target, "1", activated_counts)  # Place one bounded synthetic-token wager.


# Navigate from the authenticated shell to one game through visible UI controls.
async def navigate_to_game(page, game_id, activated_counts, ordinal=None, phase_observer=None):
    CONTROL_NAMESPACE.set("shell")  # Attribute persistent navigation actions to the shared shell.
    if callable(phase_observer):  # Emit only fixed formal subphases when a governed caller supplies an observer.
        phase_observer("navigation_return_lobby", "started")  # Attribute failure before the persistent Lobby control commits.
    await click_control(page, '[data-testid="nav-lobby"]', activated_counts, SETUP_TIMEOUT_MS)  # Return through the persistent top navigation.
    if callable(phase_observer):  # Complete the fixed control-activation subphase without affecting ordinary runs.
        phase_observer("navigation_return_lobby", "completed")  # Record successful persistent navigation activation.
        phase_observer("navigation_lobby_ready", "started")  # Attribute waiting for the catalog-owned Lobby render.
    await page.get_by_test_id("lobby").wait_for(state="visible", timeout=operation_timeout_ms(SETUP_TIMEOUT_MS))  # Require the catalog surface within any formal absolute deadline.
    if callable(phase_observer):  # Record the fixed catalog-render boundary only for governed evidence.
        phase_observer("navigation_lobby_ready", "completed")  # Record the visible Lobby state.
        phase_observer("navigation_route_open", "started")  # Attribute activation of the assigned public game route.
    entry_selector = f'[data-testid="nav-{game_id}"]' if ordinal is not None and ordinal % 10 == 0 else f'[data-testid="open-{game_id}"]'  # Route at least one hundred full-run cycles through each top-nav game button.
    await click_control(page, entry_selector, activated_counts, SETUP_TIMEOUT_MS)  # Enter through the assigned rendered navigation control.
    if callable(phase_observer):  # Separate pointer completion from asynchronous module readiness.
        phase_observer("navigation_route_open", "completed")  # Record the assigned route activation.
        phase_observer("navigation_game_ready", "started")  # Attribute the public module-ready observation.
    await page.get_by_test_id(READY_TEST_IDS[game_id]).wait_for(state="visible", timeout=operation_timeout_ms(SETUP_TIMEOUT_MS))  # Require module readiness within any formal absolute deadline.
    if callable(phase_observer):  # Complete the last fixed formal navigation subphase.
        phase_observer("navigation_game_ready", "completed")  # Record the visible game-ready boundary.
    CONTROL_NAMESPACE.set(game_id)  # Attribute all subsequent controls to the entered game module.


# Complete one terminal game play using only rendered controls.
async def play_game_ui(page, game_id, ordinal, seen_counts, activated_counts, replica_index=0):
    action_evidence = "wager_required"  # Require player-scoped game ledger evidence unless the rendered action proves it was non-wagering.
    strategy_family = strategy_family_for(game_id)  # Resolve one explicit catalog-bound dispatch before touching rendered controls.
    await inventory_controls(page, seen_counts)  # Discover ready-state controls before the play.
    await exercise_configuration_controls(page, ordinal, activated_counts)  # Cover visible fields and disclosures before the game locks them.
    await exercise_autoplay_controls(page, ordinal, activated_counts)  # Cover shared Start/Stop without leaving background play active.
    if strategy_family == "roulette":  # Exercise several table regions and one complete spin.
        chips = await enabled_locators(page, "[data-chip]")  # Discover every visible chip denomination.
        if chips:  # Rotate the selected wager unit across the complete chip stack.
            await click_locator(chips[ordinal % len(chips)], activated_counts)  # Exercise one denomination through the rendered control.
        spot_toggle = page.locator("#toggleSpots").first  # Resolve the table-hit-region visibility control.
        if await locator_ready(spot_toggle):  # Exercise the control while ending in the explicit pointer-coverage state.
            spots_are_visible = await spot_toggle.get_attribute("aria-pressed") == "true"  # Read the semantic state instead of guessing from prior clicks.
            if spots_are_visible:  # Preserve two toggle activations on cycles whose layer already starts visible.
                await click_locator(spot_toggle, activated_counts)  # Hide the inside layer through the rendered control.
            await click_locator(spot_toggle, activated_counts)  # End with every inside target visible for real pointer coverage. (issue #348)
        rebet = page.locator("#rebet").first  # Resolve the prior-round template action.
        if should_exercise_roulette_rebet(replica_index, activated_counts) and await locator_ready(rebet):  # Retry real reachable Rebet states on the primary shard until its literal floor is met.
            await click_locator(rebet, activated_counts)  # Reapply the prior template through the visible control.
            await wait_roulette_bet_drawer_minimum(page, 1)  # Require the populated template rerender before adding any new wagers.
        numbers = await enabled_locators(page, '[data-testid^="roulette-num-"]')  # Discover straight-up targets.
        if not numbers:  # Require the visible number grid.
            raise AssertionError("Roulette number targets unavailable")  # Preserve a wagering-surface failure.
        for offset in range(min(5, len(numbers))):  # Touch enough rotating number targets for double-zero-only cells to exceed the floor.
            await roulette_add_bet(page, numbers[(ordinal * 5 + offset) % len(numbers)], activated_counts)  # Exercise and serialize pointer mapping through the continuous replicated schedule.
        specials = await enabled_locators(page, "[data-dozen],[data-column],[data-outside],[data-outbtn],[data-betid],[data-call]")  # Discover table, fast, hotspot, and racetrack wagers.
        for offset in range(min(24, len(specials))):  # Give mode-specific zero targets enough capacity to exceed one hundred real activations.
            await roulette_add_bet(page, specials[(ordinal * 24 + offset) % len(specials)], activated_counts)  # Exercise and serialize each rendered hit region through the continuous replicated schedule.
        await inventory_controls(page, seen_counts)  # Discover contextual removal actions after the wager slip is populated.
        await roulette_reset_seed_and_spin(page, ordinal, activated_counts)  # Serialize contextual refund, clear-all, replacement wager, and terminal spin.
    elif strategy_family == "slots":  # Exercise one complete slot spin.
        await terminal_action(page, '[data-testid="slots-spin"]', activated_counts)  # Use the cabinet's visible spin control.
    elif strategy_family == "keno":  # Exercise ticket selection, purchase, drawing, and reset.
        new_ticket = page.get_by_test_id("keno-new-ticket")  # Resolve a persisted result-state reset.
        if await locator_ready(new_ticket):  # Normalize a restored prior draw before selecting numbers.
            await click_locator(new_ticket, activated_counts)  # Start a fresh ticket through the UI.
        mode = ordinal % 16  # Reserve one hundred-plus cycles for each quick-pick and clear-selection action.
        if mode == 0:  # Exercise the five-spot quick pick.
            await click_control(page, "#quick5", activated_counts)  # Select five numbers through the visible helper.
        elif mode == 1:  # Exercise the ten-spot quick pick.
            await click_control(page, "#quick10", activated_counts)  # Select ten numbers through the visible helper.
        else:  # Cover every individual number cell above the one-hundred activation floor.
            number_set = page.locator('[data-testid^="keno-num-"]')  # Discover all eighty rendered number targets including scroll-reachable cells.
            number_count = await number_set.count()  # Count the complete DOM board before pointer actionability checks.
            if number_count != 80:  # Reject an incomplete board without confusing off-viewport cells with missing controls.
                raise AssertionError(f"Keno number board exposed {number_count} of 80 controls")  # Preserve the exact catalog defect.
            for offset in range(7):  # Seven selections across fourteen of sixteen cycles exceed one hundred per number.
                await click_locator(number_set.nth((ordinal * 7 + offset) % number_count), activated_counts)  # Let Playwright scroll each complete-board target into view before clicking.
            if mode == 2:  # Exercise clearing a draft selection without changing the terminal cycle contract.
                await click_control(page, "#clearSel", activated_counts)  # Clear the current draft through the visible control.
                refreshed_numbers = page.locator('[data-testid^="keno-num-"]')  # Re-resolve the complete board after the selection rerender.
                for offset in range(5):  # Restore a legal bounded ticket through individual cells.
                    await click_locator(refreshed_numbers.nth((ordinal * 5 + offset) % number_count), activated_counts)  # Rebuild the draft visibly.
        await click_control(page, '[data-testid="keno-buy"]', activated_counts)  # Buy the synthetic ticket.
        if mode == 3:  # Reserve one hundred-plus cycles for the purchased-ticket refund action.
            await inventory_controls(page, seen_counts)  # Discover the conditional purchased-ticket cancellation control.
            await click_control(page, '[data-testid="keno-clear-ticket"]', activated_counts)  # Cancel the open ticket through its rendered drawer button.
            await click_control(page, '[data-testid="keno-buy"]', activated_counts)  # Repurchase the preserved draft before drawing.
        await click_control(page, '[data-testid="keno-draw"]', activated_counts)  # Draw the purchased ticket.
        await wait_any_enabled(page, ['[data-testid="keno-new-ticket"]'])  # Require the terminal result mode after the draw animation.
    elif strategy_family == "bingo":  # Exercise buy, call, and terminal reset/refund.
        await bingo_reset_to_purchase(page, activated_counts)  # Normalize any autoplay-committed session through its truthful confirmation boundary.
        await click_control(page, '[data-testid="bingo-buy"]', activated_counts)  # Buy one synthetic card.
        await click_control(page, '[data-testid="bingo-call"]', activated_counts)  # Call one ball through the UI.
        await bingo_reset_to_purchase(page, activated_counts)  # End the bounded session visibly and accept its required abandonment confirmation.
    elif strategy_family == "blackjack":  # Exercise deals and available conditional decisions.
        save_rules = page.locator("#saveRules").first  # Resolve the rendered table-rule persistence action.
        if ordinal < CONTROL_ACTIVATION_FLOOR and await locator_ready(save_rules):  # Meet the literal button floor without excessive rule writes.
            await click_locator(save_rules, activated_counts)  # Persist the currently rendered synthetic table rules.
            await wait_any_enabled(page, ['[data-testid="blackjack-deal"]'], SETUP_TIMEOUT_MS)  # Require the table to remain deal-ready.
        await click_control(page, '[data-testid="blackjack-deal"]', activated_counts)  # Deal a public hand.
        for step in range(24):  # Bound split, insurance, and hit decision sequences.
            choice = await wait_any_enabled(page, ['[data-testid="blackjack-deal"]', '[data-testid="blackjack-hit"]', '[data-testid="blackjack-stand"]', '[data-testid="blackjack-double"]', '[data-testid="blackjack-split"]', '[data-testid="blackjack-surrender"]', '[data-testid="blackjack-insurance"]', '[data-testid="blackjack-even-money"]'])  # Wait through deal and decision rerenders.
            if choice == '[data-testid="blackjack-deal"]':  # Detect terminal next-hand readiness.
                break  # Preserve one completed round.
            await inventory_controls(page, seen_counts)  # Discover every legal mutually exclusive decision before choosing one.
            actions = await enabled_locators(page, '[data-testid^="blackjack-"][data-action]')  # Discover current legal actions.
            if not actions:  # Require progress from every nonterminal state.
                raise AssertionError("Blackjack decision state exposed no legal action")  # Preserve a stranded hand.
            preferred = None  # Reserve the rare insurance and split opportunities before ordinary deficit balancing.
            for selector in ('[data-testid="blackjack-insurance"]', '[data-testid="blackjack-split"]'):  # Order the two aggregate shortfalls by observed scarcity.
                candidate = page.locator(selector).first  # Resolve the currently rendered conditional action.
                if not await locator_ready(candidate):  # Ignore a conditional action outside its legal state.
                    continue
                signature = await control_signature(candidate)  # Read the exact aggregate identity before comparing its deficit.
                if activated_counts.get(signature, 0) < CONTROL_ACTIVATION_FLOOR:  # Consume the scarce opportunity only until its literal floor is met.
                    preferred = candidate  # Preserve the real rendered action for normal pointer dispatch.
                    break
            selected_action = preferred or await least_activated_locator(actions, activated_counts)  # Fall back to the largest remaining ordinary control deficit.
            await click_locator(selected_action, activated_counts)  # Dispatch the chosen legal decision through the real pointer path.
            await page.wait_for_timeout(5)  # Allow the next decision or settlement rerender.
        else:  # Reject unbounded or cycling Blackjack state.
            raise AssertionError("Blackjack UI did not settle within 24 decisions")  # Preserve a terminal-state failure.
    elif strategy_family == "baccarat":  # Exercise rotating chip sizes, wager zones, and a coup.
        chips = await enabled_locators(page, "[data-chip]")  # Discover visible chip controls.
        if chips:  # Rotate chip coverage when the rail exposes chips.
            await click_locator(chips[ordinal % len(chips)], activated_counts)  # Select the wager unit visibly.
        bets = await enabled_locators(page, "[data-bet]")  # Discover both compact rail bets and the large table wager zones.
        if not bets:  # Require at least one rendered Baccarat wager action.
            raise AssertionError("Baccarat wager controls unavailable")  # Preserve a missing betting-surface defect.
        await click_locator(bets[ordinal % len(bets)], activated_counts)  # Rotate across every independently actionable wager button.
        await wait_any_enabled(page, ["[data-clear]"])  # Require the asynchronous wager debit to publish its removable drawer row.
        await inventory_controls(page, seen_counts)  # Discover the contextual open-bet clear action.
        await click_control(page, "[data-clear]", activated_counts)  # Refund the selected open bet through the visible drawer.
        await wait_any_enabled(page, ["[data-bet]"])  # Require the wagering surface to unlock after the refund.
        refreshed_bets = await enabled_locators(page, "[data-bet]")  # Re-resolve wager buttons after the clear rerender.
        await click_locator(refreshed_bets[ordinal % len(refreshed_bets)], activated_counts)  # Restore one bounded wager for the coup.
        await terminal_action(page, '[data-testid="baccarat-deal"]', activated_counts)  # Deal and settle the coup.
    elif strategy_family == "draw_poker":  # Exercise every explicitly registered draw-poker family member.
        modes = await enabled_locators(page, "[data-hand-count],[data-coin-count]")  # Discover pre-deal mode/coin controls.
        if modes:  # Rotate configuration coverage before the hand locks.
            await click_locator(modes[ordinal % len(modes)], activated_counts)  # Select a rendered compatible mode.
        await click_control(page, '[data-action="deal"]', activated_counts)  # Deal the source hand.
        await draw_poker_select_balanced_hold(page, seen_counts, activated_counts)  # Wait for the hand, cover every position fairly, and commit the selected hold.
        await click_control(page, '[data-action="draw"]', activated_counts)  # Draw and settle the hand.
        await wait_any_enabled(page, ['[data-action="deal"]'])  # Require next-hand readiness.
    elif strategy_family == "casino_war":  # Exercise deal and tie decisions when available.
        await click_control(page, '[data-action="deal"]', activated_counts)  # Deal one card per side.
        choice = await wait_any_enabled(page, ['[data-action="surrender"]', '[data-action="war"]', '[data-action="deal"]'])  # Detect tie or settlement.
        if choice != '[data-action="deal"]':  # Resolve only an active tie decision.
            await inventory_controls(page, seen_counts)  # Record both mutually exclusive tie actions when the rare state appears.
            tie_actions = await enabled_locators(page, '[data-action="surrender"],[data-action="war"]')  # Resolve both mutually exclusive rare actions in the live tie state.
            await click_locator(await least_activated_locator(tie_actions, activated_counts), activated_counts)  # Balance the finite tie-state budget honestly across both alternatives.
            await wait_any_enabled(page, ['[data-action="deal"]'])  # Require terminal next-deal state.
    elif strategy_family == "wager_inputs":  # Exercise every explicitly registered rotating wager-input game.
        await rotate_wager_inputs(page, ordinal, activated_counts)  # Select one catalog outcome visibly.
        action = {"big_six_wheel": "[data-spin]", "crown_and_anchor": "[data-play]", "fan_tan": "[data-play]", "over_under_7": "[data-play]", "chuck_a_luck": "[data-roll]"}[game_id]  # Resolve the module action.
        await terminal_action(page, action, activated_counts)  # Play and require next-round readiness.
    elif strategy_family == "dragon_tiger":  # Exercise rotating Dragon, Tiger, and tie wagers.
        await wait_any_enabled(page, ["[data-bet]"])  # Wait for asynchronous table data to enable the visible wager rail.
        bets = await enabled_locators(page, "[data-bet]")  # Discover the table's wager controls.
        if not bets:  # Require a visible wager surface.
            raise AssertionError("Dragon Tiger wager controls unavailable")  # Preserve a missing game action.
        await click_locator(bets[ordinal % len(bets)], activated_counts)  # Select a rotating outcome.
        await terminal_action(page, '[data-action="deal"]', activated_counts)  # Deal and settle the round.
    elif strategy_family == "red_dog":  # Exercise deal and alternating call/raise decisions.
        await click_control(page, '[data-action="deal"]', activated_counts)  # Deal the initial spread.
        choice = await wait_any_enabled(page, ['[data-action="call"]', '[data-action="raise"]', '[data-action="deal"]'])  # Detect decision or automatic result.
        if choice != '[data-action="deal"]':  # Resolve an active spread decision.
            await inventory_controls(page, seen_counts)  # Discover both legal spread decisions before selecting one.
            decision = '[data-action="raise"]' if ordinal % 2 and await locator_ready(page.locator('[data-action="raise"]').first) else '[data-action="call"]'  # Alternate legal decisions.
            await click_control(page, decision, activated_counts)  # Complete the spread visibly.
            await wait_any_enabled(page, ['[data-action="deal"]'])  # Require terminal next-round state.
    elif strategy_family == "hi_lo":  # Exercise both Higher and Lower predictions.
        await click_control(page, '[data-action="deal"]', activated_counts)  # Deal the reference card.
        await inventory_controls(page, seen_counts)  # Discover both prediction controls in their actionable state.
        await click_control(page, f'[data-guess="{"higher" if ordinal % 2 == 0 else "lower"}"]', activated_counts)  # Make a rotating visible prediction.
        await wait_any_enabled(page, ['[data-action="deal"]'])  # Require terminal next-round readiness.
    elif strategy_family == "scratch_cards":  # Exercise purchase and reveal-all settlement.
        await click_control(page, '[data-action="start"]', activated_counts)  # Buy one synthetic card.
        await wait_any_enabled(page, ['[data-testid^="scratch-cell-"]'])  # Require the asynchronous purchase to publish actionable covered cells.
        await inventory_controls(page, seen_counts)  # Discover all covered scratch cells before revealing one.
        cells = await enabled_locators(page, '[data-testid^="scratch-cell-"]')  # Discover every covered scratch position.
        if not cells:  # Reject a purchased card without rendered reveal targets.
            raise AssertionError("Scratch Card exposed no covered cells")  # Preserve the missing gameplay surface.
        await click_locator(cells[ordinal % len(cells)], activated_counts)  # Reveal one rotating position so every cell exceeds one hundred uses.
        await page.wait_for_function("() => document.querySelectorAll('.scratch-cell.is-revealed').length >= 1", timeout=operation_timeout_ms(SETUP_TIMEOUT_MS))  # Require the single-cell reveal to render before starting the terminal action.
        await click_control(page, '[data-action="reveal-all"]', activated_counts)  # Reveal every cell through the public control.
        await page.wait_for_function("() => document.querySelectorAll('.scratch-cell.is-revealed').length === 9", timeout=operation_timeout_ms(SETUP_TIMEOUT_MS))  # Require all nine authorized values to render after settlement.
        await wait_any_enabled(page, ['[data-action="start"]'])  # Require a fresh-card state.
    elif strategy_family == "sic_bo":  # Exercise rotating selections across the full bet board.
        bets = page.locator("[data-bet-id]")  # Discover every catalog wager button.
        count = await bets.count()  # Count the full rendered board.
        if count < 1:  # Refuse a missing board.
            raise AssertionError("Sic Bo bet board unavailable")  # Preserve the visual/action failure.
        for offset in range(min(4, count)):  # Place four bounded rotating wagers per shake.
            await click_locator(bets.nth((ordinal * 4 + offset) % count), activated_counts)  # Exercise distinct visible bet targets.
        await inventory_controls(page, seen_counts)  # Discover contextual wager-removal and clear actions on the populated slip.
        remove_buttons = await enabled_locators(page, "[data-remove-bet]")  # Discover selected-wager removal actions in the slip.
        if remove_buttons:  # Exercise one semantic removal on every cycle.
            await click_locator(remove_buttons[ordinal % len(remove_buttons)], activated_counts)  # Remove a rendered wager through the UI.
        clear = page.locator('[data-action="clear"]').first  # Resolve the complete selection-clear action.
        if ordinal < CONTROL_ACTIVATION_FLOOR and await locator_ready(clear):  # Exercise the button exactly through its requested floor.
            await click_locator(clear, activated_counts)  # Clear the selected slip visibly.
            refreshed_bets = page.locator("[data-bet-id]")  # Re-resolve the board after the clear state change.
            refreshed_count = await refreshed_bets.count()  # Count the rebuilt board before selecting a replacement.
            await click_locator(refreshed_bets.nth(ordinal % refreshed_count), activated_counts)  # Restore one wager for settlement.
        await terminal_action(page, '[data-action="shake"]', activated_counts)  # Roll and settle the selected wagers.
    elif strategy_family == "craps":  # Exercise one complete Pass Line round.
        await click_control(page, '[data-testid="craps-start"]', activated_counts)  # Commit the line wager through the UI.
        for _ in range(50):  # Bound exceptionally long point sequences.
            choice = await wait_any_enabled(page, ['[data-testid="craps-roll"]', '[data-testid="craps-start"]'])  # Detect roll or settlement.
            if choice == '[data-testid="craps-start"]':  # Stop at next-round readiness.
                break  # Preserve one complete round.
            await click_control(page, choice, activated_counts)  # Roll through the visible control.
        else:  # Reject an unbounded point sequence.
            raise AssertionError("Craps UI did not settle within 50 rolls")  # Preserve the failing state.
    elif strategy_family == "three_card_poker":  # Exercise deal and alternating Play/Fold decisions.
        await click_control(page, '[data-action="deal"]', activated_counts)  # Deal the three-card hand.
        await inventory_controls(page, seen_counts)  # Discover both terminal decision buttons before choosing one.
        await click_control(page, '[data-action="play"]' if ordinal % 2 else '[data-action="fold"]', activated_counts)  # Alternate terminal decisions.
        await wait_any_enabled(page, ['[data-action="deal"]'])  # Require next-hand readiness.
    elif strategy_family == "texas_holdem":  # Exercise folds and complete call-through hands.
        await click_control(page, '[data-action="start-hand"]', activated_counts)  # Start the practice hand.
        opening = await wait_any_enabled(page, ['[data-action="call"]', '[data-action="fold"]', '[data-action="start-hand"]'])  # Wait for the preflop decision or an automatic terminal result.
        if opening == '[data-action="start-hand"]':  # Accept a rare automatically settled hand.
            await inventory_controls(page, seen_counts)  # Preserve the terminal control state before leaving the branch.
            return action_evidence  # Retain fail-closed wager evidence for the committed start-hand action.
        await inventory_controls(page, seen_counts)  # Discover Call and Fold together in the opening decision state.
        if ordinal % 2 == 0:  # Cover the immediate fold path.
            await click_control(page, '[data-action="fold"]', activated_counts)  # Fold through the rendered decision.
        else:  # Cover every call street to terminal showdown.
            for _ in range(5):  # Bound preflop through river decisions.
                choice = await wait_any_enabled(page, ['[data-action="call"]', '[data-action="start-hand"]'])  # Wait for the next street or terminal showdown rerender.
                if choice == '[data-action="start-hand"]':  # Detect terminal next-hand readiness.
                    break  # Preserve the completed hand.
                await inventory_controls(page, seen_counts)  # Record the live street action before advancing it.
                await click_control(page, choice, activated_counts)  # Call the current street visibly.
            else:  # Reject a stranded practice hand.
                raise AssertionError("Texas Hold'em practice hand did not settle")  # Preserve the terminal-state failure.
        await wait_any_enabled(page, ['[data-action="start-hand"]'])  # Require the next-hand state.
    elif strategy_family == "andar_bahar":  # Exercise both table sides.
        await click_control(page, f'[data-side="{"andar" if ordinal % 2 == 0 else "bahar"}"]', activated_counts)  # Select a rotating side.
        await terminal_action(page, '[data-action="play"]', activated_counts)  # Deal and settle the round.
    elif strategy_family == "acey_deucey":  # Exercise pass and play when legally available.
        action_evidence = await acey_deucey_terminal_action(page, ordinal, seen_counts, activated_counts)  # Classify the actual rendered Pass, Play, or automatic free-boundary result.
    elif strategy_family == "caribbean_stud":  # Exercise call and fold decisions.
        await click_control(page, '[data-action="deal"]', activated_counts)  # Deal the five-card hand.
        await inventory_controls(page, seen_counts)  # Discover Call and Fold in their live decision state.
        await click_control(page, '[data-action="call"]' if ordinal % 2 else '[data-action="fold"]', activated_counts)  # Alternate decisions.
        await wait_any_enabled(page, ['[data-action="deal"]'])  # Require next-hand readiness.
    elif strategy_family == "let_it_ride":  # Exercise both Pull and Ride at both stages.
        await click_control(page, '[data-action="deal"]', activated_counts)  # Deal the initial hand.
        for stage in range(3):  # Bound two decisions plus terminal observation.
            choice = await wait_any_enabled(page, ['[data-action="deal"]', '[data-decision="ride"]', '[data-decision="pull"]'])  # Wait through each decision or settlement rerender.
            if choice == '[data-action="deal"]':  # Detect terminal next-hand state.
                break  # Preserve the settled hand.
            await inventory_controls(page, seen_counts)  # Discover Pull and Ride at every live decision stage.
            decision = '[data-decision="ride"]' if (ordinal + stage) % 2 else '[data-decision="pull"]'  # Rotate both decisions.
            await click_control(page, decision, activated_counts)  # Resolve the current stage through the UI.
        else:  # Reject an unbounded decision sequence.
            raise AssertionError("Let It Ride UI did not settle")  # Preserve the failing state.
    elif strategy_family == "casino_holdem":  # Exercise call and fold decisions.
        await click_control(page, '[data-action="deal"]', activated_counts)  # Deal the Hold'em hand.
        await inventory_controls(page, seen_counts)  # Discover both legal Hold'em decisions before choosing one.
        await click_control(page, '[data-decision="call"]' if ordinal % 2 else '[data-decision="fold"]', activated_counts)  # Alternate terminal decisions.
        await wait_any_enabled(page, ['[data-action="deal"]'])  # Require next-hand readiness.
    elif strategy_family == "plinko":  # Exercise one complete Plinko drop.
        await terminal_action(page, '[data-action="drop"]', activated_counts)  # Drop and settle through the visible control.
    elif strategy_family == "simple_terminal":  # Exercise configured choices, repeat, and one settled public action.
        await play_simple_terminal_game(page, game_id, ordinal, activated_counts)  # Use the explicit per-game selector contract.
    elif strategy_family == "lucky_grid":  # Exercise every cell through complete three-pick reveals.
        repeated = await maybe_repeat_terminal(page, ordinal, '[data-testid="lucky-grid-repeat"]', '[data-testid="lucky-grid-go"]', activated_counts)  # Use replay as the sole settlement on its bounded coverage cycles.
        if not repeated:  # Build a fresh grid selection outside repeat cycles.
            await rotate_control_group(page, "[data-chip]", ordinal, 1, activated_counts)  # Rotate every visible stake denomination.
            await rotate_control_group(page, "[data-cell]", ordinal, 3, activated_counts)  # Select three distinct cells and exceed the per-cell floor.
            await terminal_action(page, '[data-testid="lucky-grid-go"]', activated_counts)  # Reveal and settle the complete grid.
    elif strategy_family == "daily_draw_lab":  # Exercise every number through complete five-pick draws.
        repeated = await maybe_repeat_terminal(page, ordinal, '[data-testid="daily-draw-lab-repeat"]', '[data-testid="daily-draw-lab-go"]', activated_counts)  # Use replay as the sole settlement on its bounded coverage cycles.
        if not repeated:  # Build a fresh draw selection outside repeat cycles.
            await rotate_control_group(page, "[data-chip]", ordinal, 1, activated_counts)  # Rotate every visible stake denomination.
            await rotate_control_group(page, "[data-number]", ordinal, 5, activated_counts)  # Mark five distinct numbers so all thirty exceed the floor.
            await terminal_action(page, '[data-testid="daily-draw-lab-go"]', activated_counts)  # Draw and settle the marked ticket.
    elif strategy_family == "pai_gow_poker":  # Exercise repeat, manual setting, house way, and settlement.
        repeat = page.locator('[data-action="repeat"]').first  # Resolve the ready-state one-click replay control.
        use_repeat = 0 < ordinal <= CONTROL_ACTIVATION_FLOOR and await locator_ready(repeat)  # Reserve exactly one hundred reachable cycles for replay.
        if use_repeat:  # Open this round from the prior committed ante.
            await click_locator(repeat, activated_counts)  # Dispatch replay without programmatic state mutation.
        else:  # Open a fresh ante round.
            await click_control(page, '[data-action="deal"]', activated_counts)  # Deal the seven-card hand through the visible primary control.
        await wait_any_enabled(page, ['[data-action="house-way"]'])  # Require the authoritative hand-setting state.
        await inventory_controls(page, seen_counts)  # Discover all seven cards and both setting choices together.
        if ordinal % 3 == 0:  # Give House Way more than the literal activation floor.
            await click_control(page, '[data-action="house-way"]', activated_counts)  # Set and settle through the rendered automatic choice.
        else:  # Cover every manual card tile and the Set control.
            low_positions = await pai_gow_visible_low_hand_positions(page)  # Derive a legal low hand from rendered rank glyphs only.
            for position in low_positions:  # Activate both selected cards through their stable public positions.
                await click_control(page, f'[data-card-index="{position}"]', activated_counts)  # Assign one visible weak distinct-rank card to the low hand.
            await inventory_controls(page, seen_counts)  # Record the newly enabled Set control after both selections commit.
            await click_control(page, '[data-action="set"]', activated_counts)  # Submit the rendered manual split and settle.
        await wait_any_enabled(page, ['[data-action="deal"]'])  # Require terminal next-round readiness.
    elif strategy_family == "four_card_poker":  # Exercise replay and every terminal decision choice.
        repeat = page.locator('[data-action="repeat"]').first  # Resolve replay from the ready or settled state.
        if 0 < ordinal <= CONTROL_ACTIVATION_FLOOR and await locator_ready(repeat):  # Close the repeat deficit without opening a second round.
            await click_locator(repeat, activated_counts)  # Re-deal the stored wagers through the public control.
        else:  # Open one fresh decision round.
            await click_control(page, '[data-deal]', activated_counts)  # Deal through the visible wager-owned action.
        await wait_any_enabled(page, ["[data-fold]", "[data-play]"])  # Require the authoritative decision state.
        await inventory_controls(page, seen_counts)  # Discover Fold and every Play multiplier before choosing.
        decisions = await enabled_locators(page, "[data-fold],[data-play]")  # Resolve every legal terminal choice.
        await click_locator(await least_activated_locator(decisions, activated_counts), activated_counts)  # Balance all decisions above the literal floor.
        await wait_any_enabled(page, ["[data-deal]"])  # Require terminal next-round readiness.
    elif strategy_family == "mississippi_stud":  # Exercise replay plus balanced choices across every street.
        repeat = page.locator("[data-repeat]").first  # Resolve replay from the ready or settled state.
        if 0 < ordinal <= CONTROL_ACTIVATION_FLOOR and await locator_ready(repeat):  # Close the repeat deficit without opening a second round.
            await click_locator(repeat, activated_counts)  # Re-deal the stored ante through the public control.
        else:  # Open one fresh multi-street round.
            await click_control(page, "[data-deal]", activated_counts)  # Deal through the rendered ante action.
        for _street in range(4):  # Bound three decisions plus terminal observation.
            choice = await wait_any_enabled(page, ["[data-deal]", "[data-fold]", "[data-bet]"])  # Wait for settlement or the next authoritative street.
            if choice == "[data-deal]":  # Detect terminal next-round readiness.
                break  # Preserve one completed round.
            await inventory_controls(page, seen_counts)  # Discover Fold and every legal multiplier on this street.
            decisions = await enabled_locators(page, "[data-fold],[data-bet]")  # Resolve the complete current decision set.
            await click_locator(await least_activated_locator(decisions, activated_counts), activated_counts)  # Spend the largest remaining real control deficit.
            await page.wait_for_timeout(5)  # Allow the next street or settlement rerender before polling again.
        else:  # Reject a stranded or cycling stud round.
            raise AssertionError("Mississippi Stud UI did not settle within three decisions")  # Preserve one bounded terminal-state failure.
    elif strategy_family == "teen_patti":  # Exercise replay plus both Play and Fold.
        repeat = page.locator("[data-repeat]").first  # Resolve replay from the ready or settled state.
        if 0 < ordinal <= CONTROL_ACTIVATION_FLOOR and await locator_ready(repeat):  # Close the repeat deficit without opening a second round.
            await click_locator(repeat, activated_counts)  # Re-deal the stored ante through the public control.
        else:  # Open one fresh decision round.
            await click_control(page, "[data-deal]", activated_counts)  # Deal through the visible ante action.
        await wait_any_enabled(page, ["[data-fold]", "[data-play]"])  # Require the authoritative decision state.
        await inventory_controls(page, seen_counts)  # Discover both terminal choices before selecting one.
        decisions = await enabled_locators(page, "[data-fold],[data-play]")  # Resolve both legal visible decisions.
        await click_locator(await least_activated_locator(decisions, activated_counts), activated_counts)  # Balance Play and Fold above the floor.
        await wait_any_enabled(page, ["[data-deal]"])  # Require terminal next-round readiness.
    else:  # Refuse silent catalog omissions.
        raise AssertionError(f"no UI cycle strategy implementation for family {strategy_family}")  # Force executable dispatch for every registered family.
    await inventory_controls(page, seen_counts)  # Discover terminal and conditional-state controls after the play.
    return action_evidence  # Return one fixed action-aware ledger expectation without identity or gameplay payload data.


# Attach credential-free diagnostics to one test-owned browser page.
def attach_page_diagnostics(page, diagnostics, anonymous_probe_active=None):
    state = {"anonymous_probe_seen": False, "anonymous_console_seen": False}  # Track the expected pre-login identity probe signals.

    def on_console(message):  # Capture browser console errors only.
        if message.type == "error":  # Ignore ordinary application information.
            in_anonymous_window = bool(anonymous_probe_active()) if callable(anonymous_probe_active) else not state["anonymous_console_seen"]  # Resolve either caller-owned authentication state or the legacy single-probe allowance.
            expected_probe = str(message.text) == "Failed to load resource: the server responded with a status of 401 (Unauthorized)" and in_anonymous_window  # Recognize only a pre-authentication current-user probe.
            if expected_probe:  # Exclude expected anonymous bootstrap or hydration diagnostics.
                state["anonymous_console_seen"] = True  # Ensure later unauthorized resource failures remain visible.
                return  # Preserve only unexpected console errors.
            diagnostics["console_errors"][str(message.text)[:300]] += 1  # Group bounded public console messages.

    def on_page_error(error):  # Capture uncaught JavaScript errors.
        diagnostics["page_errors"][safe_error(error)] += 1  # Group bounded local-only diagnostics.

    def on_response(response):  # Capture unexpected API failures observed by the browser.
        if "/api/" not in response.url or response.status < 400:  # Ignore assets and successful API traffic.
            return  # Preserve only protected-request failures.
        path = "/" + response.url.split("/", 3)[-1].split("?", 1)[0]  # Strip origin and query data.
        in_anonymous_window = bool(anonymous_probe_active()) if callable(anonymous_probe_active) else not state["anonymous_probe_seen"]  # Resolve exact caller-owned pre-authentication state or the legacy one-response allowance.
        expected_probe = response.request.method == "GET" and path == "/api/v2/me" and response.status == 401 and in_anonymous_window  # Recognize only anonymous current-user probes.
        if expected_probe:  # Exclude expected pre-login bootstrap and hydration responses.
            state["anonymous_probe_seen"] = True  # Ensure later current-user failures remain visible.
            return  # Preserve only unexpected failures.
        diagnostics["http_failures"][f"{response.status} {response.request.method} {path}"] += 1  # Group sanitized route evidence.

    page.on("console", on_console)  # Observe console errors without changing behavior.
    page.on("pageerror", on_page_error)  # Observe uncaught page exceptions.
    page.on("response", on_response)  # Observe failed browser-owned API requests.


# Inspect one rendered game for overflow, truncation, and clipped enabled controls.
async def geometry_scan(page):
    expression = r"""() => { const viewport = { width: innerWidth, height: innerHeight }; const originalScroll = { x: scrollX, y: scrollY }; const documentOverflowX = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth; const brand = document.querySelector('.brand-text,.brand-name,[data-testid="premium-brand"]'); const brandTruncated = Boolean(brand && brand.scrollWidth > brand.clientWidth + 1); const clipped = []; const scrollReachable = []; const occluded = []; const controls = [...document.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),summary')]; for (const node of controls) { if (!node.getClientRects().length || node.offsetParent === null || getComputedStyle(node).visibility === 'hidden' || (node.tagName !== 'SUMMARY' && node.closest('details:not([open])'))) continue; const sig = String(node.getAttribute('data-testid') || node.getAttribute('data-action') || node.getAttribute('data-bet-id') || node.id || node.getAttribute('aria-label') || node.textContent || node.tagName).trim().replace(/\s+/g,' ').slice(0,100); let targetRect = node.getBoundingClientRect(); let ancestor = node.parentElement; let reachableByScroller = false; let inaccessible = false; const ancestorScrolls = []; while (ancestor && ancestor !== document.body) { const style = getComputedStyle(ancestor); const ancestorRect = ancestor.getBoundingClientRect(); const outsideY = targetRect.bottom > ancestorRect.bottom + 4 || targetRect.top < ancestorRect.top - 4; const outsideX = targetRect.right > ancestorRect.right + 4 || targetRect.left < ancestorRect.left - 4; const overflowY = style.overflowY === 'visible' ? style.overflow : style.overflowY; const overflowX = style.overflowX === 'visible' ? style.overflow : style.overflowX; const scrollableY = ['auto','scroll'].includes(overflowY) && ancestor.scrollHeight > ancestor.clientHeight + 1; const scrollableX = ['auto','scroll'].includes(overflowX) && ancestor.scrollWidth > ancestor.clientWidth + 1; ancestorScrolls.push({ node: ancestor, left: ancestor.scrollLeft, top: ancestor.scrollTop, scrollableX, scrollableY }); if ((outsideY && scrollableY) || (outsideX && scrollableX)) { reachableByScroller = true; targetRect = ancestorRect; } else if ((outsideY && ['hidden','clip'].includes(overflowY)) || (outsideX && ['hidden','clip'].includes(overflowX))) { inaccessible = true; break; } ancestor = ancestor.parentElement; } if (inaccessible) { clipped.push(sig); continue; } if (reachableByScroller) scrollReachable.push(sig); node.scrollIntoView({ block: 'center', inline: 'center' }); for (const saved of ancestorScrolls) saved.node.scrollTo(saved.scrollableX ? saved.node.scrollLeft : saved.left, saved.scrollableY ? saved.node.scrollTop : saved.top); const actionRect = node.getBoundingClientRect(); const x = Math.max(0, Math.min(innerWidth - 1, actionRect.left + actionRect.width / 2)); const y = Math.max(0, Math.min(innerHeight - 1, actionRect.top + actionRect.height / 2)); const top = document.elementFromPoint(x, y); const labelOwnsNode = Boolean(top?.closest('label')?.contains(node)); if (top && top !== node && !node.contains(top) && !labelOwnsNode) occluded.push(sig); for (const saved of ancestorScrolls) saved.node.scrollTo(saved.left, saved.top); scrollTo(originalScroll.x, originalScroll.y); } scrollTo(originalScroll.x, originalScroll.y); return { viewport, document_overflow_x_px: Math.max(0, Math.round(documentOverflowX)), brand_truncated: brandTruncated, clipped_enabled_control_count: clipped.length, clipped_enabled_controls: [...new Set(clipped)].slice(0,100), scroll_reachable_enabled_control_count: scrollReachable.length, scroll_reachable_enabled_controls: [...new Set(scrollReachable)].slice(0,100), occluded_enabled_control_count: occluded.length, occluded_enabled_controls: [...new Set(occluded)].slice(0,100) }; }"""  # Detect clipping and occlusion without letting scrollIntoView mutate hidden-overflow axes or later viewport evidence. (issue #348)
    return await page.evaluate(expression)  # Return sanitized geometry findings.


# Inspect game-declared essential stage nodes for missing paint, stage escape, and hidden-ancestor clipping.
async def essential_stage_scan(page, game_id):
    contract = ESSENTIAL_STAGE_CONTRACTS.get(game_id)  # Resolve only an explicit game-owned completeness contract.
    if not contract:  # Preserve ordinary control geometry for games without a declared non-control stage.
        return []  # Return one uniform clean result for aggregate accounting.
    expression = r"""contract => { const failures = []; const stage = document.querySelector(contract.stage); if (!stage) return [{ selector: contract.stage, reason: 'stage missing' }]; const stageRect = stage.getBoundingClientRect(); const outside = (rect, owner) => rect.left < owner.left - 1 || rect.right > owner.right + 1 || rect.top < owner.top - 1 || rect.bottom > owner.bottom + 1; const painted = (node, style, rect) => node.getClientRects().length && style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0; for (const selector of contract.contained_items) { const node = document.querySelector(selector); if (!node) { failures.push({ selector, reason: 'essential node missing' }); continue; } const style = getComputedStyle(node); const rect = node.getBoundingClientRect(); if (!painted(node, style, rect)) { failures.push({ selector, reason: 'essential node not painted' }); continue; } if (outside(rect, stageRect)) failures.push({ selector, reason: 'essential node escaped stage' }); let ancestor = node.parentElement; while (ancestor && ancestor !== document.body) { const ancestorStyle = getComputedStyle(ancestor); const ancestorRect = ancestor.getBoundingClientRect(); const overflowY = ancestorStyle.overflowY === 'visible' ? ancestorStyle.overflow : ancestorStyle.overflowY; const overflowX = ancestorStyle.overflowX === 'visible' ? ancestorStyle.overflow : ancestorStyle.overflowX; const clippedY = (rect.top < ancestorRect.top - 1 || rect.bottom > ancestorRect.bottom + 1) && ['hidden','clip'].includes(overflowY); const clippedX = (rect.left < ancestorRect.left - 1 || rect.right > ancestorRect.right + 1) && ['hidden','clip'].includes(overflowX); if (clippedY || clippedX) { failures.push({ selector, reason: 'essential node clipped by hidden ancestor' }); break; } ancestor = ancestor.parentElement; } } for (const [selector, ownerSelector] of Object.entries(contract.paint_items)) { const node = document.querySelector(selector); const owner = document.querySelector(ownerSelector); if (!node) { failures.push({ selector, reason: 'essential node missing' }); continue; } if (!owner) { failures.push({ selector: ownerSelector, reason: 'visual owner missing' }); continue; } const style = getComputedStyle(node); const rect = node.getBoundingClientRect(); const ownerRect = owner.getBoundingClientRect(); if (!painted(node, style, rect)) { failures.push({ selector, reason: 'essential node not painted' }); continue; } const centerInside = rect.left + rect.width / 2 >= ownerRect.left - 1 && rect.left + rect.width / 2 <= ownerRect.right + 1 && rect.top + rect.height / 2 >= ownerRect.top - 1 && rect.top + rect.height / 2 <= ownerRect.bottom + 1; const coversOwner = rect.width >= ownerRect.width * contract.paint_min_ratio && rect.height >= ownerRect.height * contract.paint_min_ratio; if (!centerInside || !coversOwner) failures.push({ selector, reason: 'essential node does not cover visual owner' }); } return failures.filter((failure, index, all) => all.findIndex(candidate => candidate.selector === failure.selector && candidate.reason === failure.reason) === index); }"""  # Detect stage incompleteness while treating a rotating 90%-sized square clipped into a circle as complete paint rather than false overflow.
    return await page.evaluate(expression, contract)  # Return bounded selector-and-reason evidence only.


# Create one isolated disposable runtime copy outside the source checkout.
def prepare_deployment(args, run_id, shard_label):
    parent = Path(args.deployment_root).expanduser().resolve()  # Resolve the harness-owned temporary parent.
    source = ROOT.resolve()  # Resolve the frozen source snapshot.
    if str(parent).lower().startswith(str(source).lower()):  # Prevent recursive copies into the worktree.
        raise RuntimeError("deployment root must not be inside the source checkout")  # Fail before mutation.
    parent.mkdir(parents=True, exist_ok=True)  # Create the disposable parent.
    target = parent / f"casino-ui-50k-{run_id}-{shard_label}"  # Give each worker one isolated runtime.
    ignored = shutil.ignore_patterns(".git", "codex", "logs", "__pycache__", "*.pyc")  # Exclude repository metadata, prior evidence, and caches that the runtime never reads.
    shutil.copytree(source, target, ignore=ignored)  # Copy the exact application source into the isolated disposable runtime.
    return target  # Return the shard-owned runtime tree.


# Provision one high-balance synthetic user through the Admin boundary.
def create_synthetic_user(client, shard_label, run_id, locale):
    email = f"ui-50k-{run_id}-{shard_label}@example.test"  # Use a non-routable synthetic identifier.
    password = f"Ui50k-{run_id}-{shard_label}-Only"  # Generate a local-only shard credential.
    payload = {"email": email, "password": password, "display_name": f"UI 50k {shard_label}", "initial_tokens": 1_000_000, "terms_accepted": True, "language": locale, "format_locale": locale}  # Provide ample fake tokens for bounded play.
    created = client.call("/api/v1/admin/users", "POST", payload)  # Provision through the documented Admin API.
    return {"email": email, "password": password, "user_id": created["user"]["user_id"], "player_id": created["user"]["player_id"]}  # Retain in-memory credentials and canonical IDs only.


# Log one synthetic user in through the rendered authentication form.
async def login_through_ui(page, base_url, user, locale, activated_counts, *, navigate=True, deadline_ms=None, phase_observer=None):  # Preserve ordinary callers while exposing formal-only gate reuse, deadline, and phase seams.
    # Preserve the ordinary per-operation timeout unless a formal profile supplies one absolute deadline.
    deadline_at = None if deadline_ms is None else time.perf_counter() + (int(deadline_ms) / 1000)

    # Publish fixed low-cardinality phase transitions only when the caller supplies an aggregate observer.
    def observe_phase(name, status):
        # Avoid changing ordinary browser evidence when no formal observer is configured.
        if phase_observer is not None:
            # Forward only the caller-owned fixed phase and status labels.
            phase_observer(name, status)

    # Calculate the remaining absolute formal deadline or retain the established ordinary timeout.
    def operation_timeout():
        # Keep ordinary long-suite behavior unchanged outside the formal concurrent profile.
        if deadline_at is None:
            # Return the established setup timeout for each independent operation.
            return SETUP_TIMEOUT_MS
        # Convert the remaining wall time into the positive millisecond value expected by Playwright.
        remaining_ms = int((deadline_at - time.perf_counter()) * 1000)
        # Fail with one bounded diagnostic when the formal aggregate deadline is exhausted.
        if remaining_ms <= 0:
            # Avoid leaking account, page, URL, or selector state in the terminal artifact.
            raise TimeoutError("formal login deadline exceeded")
        # Preserve at least one millisecond for the next already-started formal phase.
        return max(1, remaining_ms)

    # Attribute the one-time rendered login controls to authentication lifecycle evidence.
    CONTROL_NAMESPACE.set("auth")
    # Load the public login UI only for callers that have not already rendered the gate.
    if navigate:
        # Record the optional shell-navigation phase for aggregate formal diagnostics.
        observe_phase("shell_navigation", "started")
        # Load the public login UI through the established ordinary or remaining formal timeout.
        await page.goto(base_url, wait_until="domcontentloaded", timeout=operation_timeout())
        # Record terminal shell-navigation completion without URL or account identity.
        observe_phase("shell_navigation", "completed")
    # Record the fixed login-gate phase before inspecting the existing rendered shell.
    observe_phase("login_gate", "started")
    # Require the rendered login gate even when a formal caller reuses its pre-barrier page.
    await page.get_by_test_id("login-gate").wait_for(state="visible", timeout=operation_timeout())
    # Record successful gate reuse before localized form mutation begins.
    observe_phase("login_gate", "completed")
    # Record the localized-selector phase.
    observe_phase("locale_selection", "started")
    # Resolve the auth language selector.
    locale_select = page.get_by_test_id("auth-locale-select")
    # Select the shard locale through the UI.
    await locale_select.select_option(locale, timeout=operation_timeout())
    # Count the visible locale change.
    activated_counts[await control_signature(locale_select)] += 1
    # Record the completed localized-selector phase.
    observe_phase("locale_selection", "completed")
    # Record the credential-entry phase without publishing account data.
    observe_phase("credential_entry", "started")
    # Enter the synthetic email after the locale rerender.
    await fill_control(page.get_by_test_id("login-email"), user["email"], activated_counts, operation_timeout())
    # Enter the local-only password after the locale rerender.
    await fill_control(page.get_by_test_id("login-password"), user["password"], activated_counts, operation_timeout())
    # Record terminal credential entry without retaining values.
    observe_phase("credential_entry", "completed")
    # Record the simulator-terms phase.
    observe_phase("terms_acceptance", "started")
    # Resolve the fake-money acknowledgement.
    terms = page.get_by_test_id("login-terms-check")
    # Accept simulator terms through the form.
    await terms.check(timeout=operation_timeout())
    # Count the successful checkbox activation.
    activated_counts[await control_signature(terms)] += 1
    # Record terminal terms acceptance.
    observe_phase("terms_acceptance", "completed")
    # Record the rendered login-response phase.
    observe_phase("login_response", "started")
    # Observe the form-owned login request beneath the same absolute formal deadline.
    async with page.expect_response(lambda response: response.url.endswith("/api/v2/auth/login") and response.request.method == "POST", timeout=operation_timeout()) as response_info:  # Observe the form-owned login request beneath the same absolute formal deadline.
        # Submit through the rendered button.
        await click_locator(page.get_by_test_id("login-submit"), activated_counts, operation_timeout())
    # Resolve the authentication response.
    response = await response_info.value
    # Fail promptly on rejected login.
    if response.status >= 400:
        # Preserve status without credentials.
        raise AssertionError(f"UI login endpoint returned HTTP {response.status}")
    # Record successful form response before authenticated shell hydration.
    observe_phase("login_response", "completed")
    # Record the authenticated-lobby phase.
    observe_phase("authenticated_lobby", "started")
    # Require the authenticated catalog.
    await page.get_by_test_id("lobby").wait_for(state="visible", timeout=operation_timeout())
    # Read the UI-bound identity only.
    browser_identity = await page.evaluate("window.CasinoCurrentUser?.user?.email || ''")
    # Detect session leakage or incorrect binding.
    if str(browser_identity).lower() != user["email"].lower():
        # Fail without exposing identity values.
        raise AssertionError("browser identity did not match the synthetic shard user")
    # Record terminal authenticated-shell readiness.
    observe_phase("authenticated_lobby", "completed")
    # Attribute the authenticated lobby and subsequent navigation to the shared shell.
    CONTROL_NAMESPACE.set("shell")


# Save one JSON artifact atomically enough for local test review.
def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the artifact parent exists.
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")  # Persist readable machine evidence.


# Execute every assigned UI cycle for one isolated catalog game.
async def run_game_shard(playwright, semaphore, args, game_id, game_index, replica_index, quota, cycle_start, run_id, source_commit):
    async with semaphore:  # Bound simultaneous browsers, servers, and file-backed runtimes.
        shard_started = time.perf_counter()  # Measure the complete harness-owned worker interval, including cleanup.
        locale = "en-US" if game_index % 2 == 0 else "ru-RU"  # Distribute the two implemented locales deterministically.
        report = {"game": game_id, "game_index": game_index, "replica_index": replica_index, "locale": locale, "quota": quota, "global_cycle_start": cycle_start, "global_cycle_end": cycle_start + quota - 1, "source_commit": source_commit, "attempted": 0, "attempted_actions": 0, "completed": 0, "failed": 0, "failed_attempts": 0, "status": "FAIL", "requirements": list(REQUIREMENT_IDS)}  # Start fail-closed shard evidence bound to the exact source.
        seen_counts = Counter()  # Count actionable controls observed across states.
        activated_counts = Counter()  # Count controls activated through the browser UI.
        failure_counts = Counter()  # Group repeated UI failure signatures.
        failure_first_cycle = {}  # Preserve the first global cycle for each failure class.
        diagnostics = {"console_errors": Counter(), "page_errors": Counter(), "http_failures": Counter()}  # Collect browser-owned failure signals.
        latencies = []  # Record successful full-cycle latency.
        deployment = None  # Track the shard-owned runtime copy.
        proc = None  # Track the exact loopback server process.
        client = None  # Track the Admin evidence client and base URL.
        browser = None  # Track the test-owned Chromium process.
        context = None  # Track the isolated cookie/session context.
        user = None  # Track canonical synthetic account IDs for isolation evidence.
        screenshot_root = Path(args.evidence_root).expanduser().resolve()  # Resolve local visual evidence root.
        shard_label = f"{game_id}-r{replica_index}"  # Create a unique worker label without changing the canonical game identity.
        shard_report_path = Path(args.shard_report_root).expanduser().resolve() / f"{game_index:02d}-{shard_label}.json"  # Resolve the per-worker JSON artifact.
        try:  # Preserve one terminal report across setup, cycles, evidence, and cleanup.
            deployment = prepare_deployment(args, run_id, shard_label)  # Create the isolated protected-source runtime.
            proc, client = start_ui_server(deployment)  # Start one tracked loopback-only Casino server without log-pipe backpressure.
            client.call("/api/v1/casino/reset", "POST", {})  # Reset only the disposable shard data.
            client.login_default_user()  # Restore the Admin evidence session after reset.
            operations = client.call("/api/v2/admin/operations")  # Bind the shard to readiness and build evidence.
            if not operations.get("ready"):  # Refuse testing a degraded runtime.
                raise AssertionError("operations readiness was not green before UI cycles")  # Preserve the failing gate.
            user = create_synthetic_user(client, shard_label, run_id, locale)  # Provision one isolated high-balance player.
            browser = await playwright.chromium.launch(headless=not args.headed)  # Launch one real Chromium process.
            context = await browser.new_context(viewport={"width": 1920, "height": 1080}, reduced_motion="reduce")  # Use stable desktop soak geometry and reduced motion.
            page = await context.new_page()  # Give this game shard one real browser page.
            attach_page_diagnostics(page, diagnostics)  # Observe browser errors without changing behavior.
            await login_through_ui(page, client.base_url, user, locale, activated_counts)  # Authenticate through the real form.
            await inventory_controls(page, seen_counts)  # Discover the authenticated lobby and shell controls.
            for ordinal in range(quota):  # Complete every assigned global UI cycle or exhaust its bounded retry evidence.
                global_cycle = cycle_start + ordinal  # Resolve the globally unique test ID.
                scheduled_ordinal = coverage_ordinal(game_id, ordinal, global_cycle)  # Continue replicated Roulette coverage across worker range boundaries.
                report["attempted"] += 1  # Count each unique assigned cycle ID exactly once.
                cycle_completed = False  # Keep the cycle fail closed until a terminal UI state is observed.
                for attempt_number in range(1, args.max_attempts_per_cycle + 1):  # Retry only the same global cycle within a strict bound.
                    report["attempted_actions"] += 1  # Count every real browser play attempt, including recovery attempts.
                    started = time.perf_counter()  # Start end-to-end navigation and gameplay timing.
                    try:  # Continue after bounded product failures so exact completion can still be measured.
                        await navigate_to_game(page, game_id, activated_counts, scheduled_ordinal)  # Navigate visibly while rotating the complete game-local coverage schedule.
                        await play_game_ui(page, game_id, scheduled_ordinal, seen_counts, activated_counts, replica_index)  # Complete one rendered-control play using the continuous replicated schedule and shard-owned rare-control budget.
                        latencies.append(time.perf_counter() - started)  # Record successful full-cycle latency.
                        report["completed"] += 1  # Count only the first terminal completion for this global cycle.
                        cycle_completed = True  # Prevent any duplicate completion for this ID.
                        break  # Advance to the next unique global cycle.
                    except Exception as exc:  # Classify a product or route failure without aborting the shard.
                        signature = safe_error(exc)  # Bound and normalize the failure class.
                        failure_counts[signature] += 1  # Count repeated occurrences.
                        failure_first_cycle.setdefault(signature, global_cycle)  # Preserve the first deterministic reproduction ID.
                        report["failed_attempts"] += 1  # Count the failed browser action separately from completed-cycle accounting.
                        if failure_counts[signature] == 1:  # Capture only one screenshot per distinct failure class.
                            path = screenshot_root / "before_failure" / f"{game_index:02d}-{shard_label}-{len(failure_first_cycle):02d}.png"  # Resolve sanitized failure evidence.
                            path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the evidence directory exists.
                            await page.screenshot(path=str(path), full_page=True)  # Capture the failing visible state.
                        try:  # Recover through a public page reload without mutating server state directly.
                            await page.reload(wait_until="domcontentloaded", timeout=SETUP_TIMEOUT_MS)  # Rebuild the current route and session shell.
                            await page.locator("body").wait_for(state="visible", timeout=SETUP_TIMEOUT_MS)  # Require only a reconstructed document before retry.
                        except Exception:  # Let the next bounded retry use navigation recovery from the current document.
                            pass  # Preserve the original failure rather than replacing it with recovery noise.
                if not cycle_completed:  # Preserve a cycle that never reached a terminal UI state.
                    report["failed"] += 1  # Count one uncompleted global cycle after all bounded attempts.
                if (ordinal + 1) % args.progress_every == 0 or ordinal + 1 == quota:  # Emit bounded progress for long monitoring.
                    print(f"UI50K game={game_id} replica={replica_index} assigned={ordinal + 1}/{quota} actions={report['attempted_actions']} completed={report['completed']} uncompleted={report['failed']} failed_attempts={report['failed_attempts']}", flush=True)  # Report only sanitized counts.
            state = call_post_soak_admin_evidence(client, f"/api/v2/admin/users/{user['user_id']}/state")  # Reauthenticate after the long soak before reading canonical user state.
            report["isolation"] = {"player_match": state["player_id"] == user["player_id"], "nonnegative_balance": float(state["token_balance"]) >= 0, "ledger_events": int(state["recent_ledger_count"])}  # Store sanitized identity/wallet invariants.
            try:  # Capture one representative terminal surface even when some cycles failed.
                await navigate_to_game(page, game_id, activated_counts)  # Re-enter the game through visible navigation.
            except Exception:  # Preserve the current failing page if route recovery is unavailable.
                pass  # Let the screenshot and geometry scan document the actual state.
            report["visuals"] = []  # Preserve one geometry result and screenshot reference per governed viewport.
            for viewport in VIEWPORTS:  # Inspect every registered game at desktop, compact desktop, tablet, and mobile widths.
                await page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})  # Apply the complete governed visual matrix row.
                artifact_name = f"{game_index:02d}-{shard_label}-{viewport['id']}-{locale}.png"  # Build a sanitized stable filename without a private host path.
                evidence_path = screenshot_root / "representative" / artifact_name  # Resolve the representative evidence path.
                evidence_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the evidence directory exists.
                await page.screenshot(path=str(evidence_path), full_page=True)  # Save reviewable UI evidence.
                geometry = await geometry_scan(page)  # Inspect controls and document overflow without retaining scroll mutations.
                geometry["essential_stage_failures"] = await essential_stage_scan(page, game_id)  # Reject clipped game theater that contains no enabled controls.
                report["visuals"].append({"viewport": viewport, "geometry": geometry, "artifact": f"representative/{artifact_name}", "evidence_class": "after_failure_recovery" if failure_counts else "after_pass"})  # Store complete automated geometry evidence without private paths or mislabeled recovered failures.
            post_operations = call_post_soak_admin_evidence(client, "/api/v2/admin/operations")  # Reauthenticate again before the terminal readiness proof.
            report["operations_ready_after"] = bool(post_operations.get("ready"))  # Preserve post-load readiness.
            report["status"] = "PASS" if report["completed"] == quota and not report["failed"] and not failure_counts and report["isolation"]["player_match"] and report["isolation"]["nonnegative_balance"] and report["isolation"]["ledger_events"] > 0 and report["operations_ready_after"] and not diagnostics["console_errors"] and not diagnostics["page_errors"] and not diagnostics["http_failures"] else "FAIL"  # Evaluate every gameplay, identity, readiness, and browser-diagnostic shard gate.
        except Exception as exc:  # Capture fatal setup, browser, or evidence failures.
            report["fatal_error"] = {"message": safe_error(exc), "traceback_summary": safe_error(traceback.format_exc())}  # Preserve a bounded sanitized traceback summary.
            report["failed"] = max(report["failed"], quota - report["completed"])  # Account for all uncompleted assigned tests.
            report["status"] = "FAIL"  # Keep the shard fail closed.
        finally:  # Close only test-owned resources and always persist the shard report.
            if context is not None:  # Close the isolated session context when created.
                await context.close()  # Revoke cookies and release its page.
            if browser is not None:  # Close the shard-owned Chromium process when launched.
                await browser.close()  # Release the browser process and children.
            if proc is not None and client is not None:  # Stop only this shard's tracked server.
                try:  # Preserve cleanup failure as a release-gate failure.
                    report["listener_cleanup"] = stop_server(proc, client)  # Verify the exact loopback listener closed.
                except Exception as cleanup_exc:  # Record failed cleanup without touching unrelated runtimes.
                    report["listener_cleanup"] = {"closed": False, "error": safe_error(cleanup_exc)}  # Preserve bounded cleanup evidence.
                    report["status"] = "FAIL"  # Refuse a passing shard with unverified cleanup.
            if deployment is not None and deployment.exists() and not args.keep_deployments:  # Remove only this shard-owned runtime.
                shutil.rmtree(deployment, onerror=clear_readonly_and_retry)  # Clean synthetic data after listener closure.
            report["control_seen_counts"] = dict(sorted(seen_counts.items()))  # Persist deterministic control discovery.
            report["control_activated_counts"] = dict(sorted(activated_counts.items()))  # Persist deterministic UI activation coverage.
            report["failure_counts"] = dict(failure_counts.most_common())  # Persist grouped product failures.
            report["failure_first_cycle"] = failure_first_cycle  # Preserve deterministic first reproduction IDs.
            report["latency"] = latency_summary(latencies)  # Persist successful-cycle performance evidence.
            report["browser_diagnostics"] = {name: dict(counter.most_common()) for name, counter in diagnostics.items()}  # Persist grouped browser signals.
            report["ui_process_seconds"] = round(time.perf_counter() - shard_started, 3)  # Expose profile-staleness evidence without relying only on hosted timestamps.
            write_json(shard_report_path, report)  # Save the terminal per-game artifact.
        return report  # Return the sanitized shard evidence to the aggregate controller.


# Parse repeatable smoke, catalog, and full qualification options.
def parse_args():
    parser = argparse.ArgumentParser(description="Run real-browser UI cycles across every registered Casino game.")  # Create the CLI parser.
    parser.add_argument("--total-cycles", type=int, default=50_000, help="Exact total UI cycle attempts distributed across selected games.")  # Configure smoke or full volume.
    parser.add_argument("--parallel", type=int, default=4, help="Maximum isolated game shards active together.")  # Bound local CPU, memory, and listeners.
    parser.add_argument("--only-games", default="", help="Optional comma-separated catalog game IDs for focused rehearsal.")  # Enable bounded strategy debugging.
    parser.add_argument("--deployment-root", default=str(Path(tempfile.gettempdir()) / "casino-ui-50000"), help="Parent for disposable runtime copies.")  # Keep runtime writes outside the source checkout on every supported runner.
    parser.add_argument("--report", default=str(ROOT / "logs" / "test-runs" / "ui_50000.json"), help="Aggregate JSON report path.")  # Configure terminal evidence.
    parser.add_argument("--shard-report-root", default=str(ROOT / "logs" / "test-runs" / "ui_50000_shards"), help="Per-game JSON artifact directory.")  # Preserve recoverable shard handbacks.
    parser.add_argument("--evidence-root", default=str(ROOT / "logs" / "test-runs" / "ui_50000_visual"), help="Representative and failure screenshot directory.")  # Configure visual evidence.
    parser.add_argument("--progress-every", type=int, default=250, help="Progress interval within each game shard.")  # Keep long-run monitoring bounded.
    parser.add_argument("--roulette-replicas", type=int, default=4, help="Independent Roulette workers that share its exact assigned quota.")  # Parallelize the interaction-dense Roulette board.
    parser.add_argument("--replicate-games", default="", help="Optional comma-separated non-Roulette game IDs to split across extra workers.")  # Accelerate safe resumption of unfinished game ranges.
    parser.add_argument("--game-replicas", type=int, default=4, help="Worker count for each game selected by --replicate-games.")  # Bound resumed per-game parallelism.
    parser.add_argument("--resume-shards", action="store_true", help="Reuse complete compatible terminal reports from --shard-report-root.")  # Preserve verified work across bounded controller runs.
    parser.add_argument("--max-attempts-per-cycle", type=int, default=3, help="Maximum UI recovery attempts for one unique global cycle ID.")  # Bound retries while preserving exact completed-cycle evidence.
    parser.add_argument("--headed", action="store_true", help="Show test browsers for focused debugging only.")  # Keep long qualification headless.
    parser.add_argument("--keep-deployments", action="store_true", help="Preserve disposable runtimes for explicit local debugging.")  # Allow opt-in post-failure inspection.
    parser.add_argument("--allocation-index", type=int, default=None, help="Run exactly one deterministic formal worker allocation.")  # Let non-local CI distribute the immutable 50,000-cycle assignment.
    parser.add_argument("--aggregate-only", action="store_true", help="Aggregate a complete downloaded formal shard set without launching a browser.")  # Separate terminal accounting from worker execution.
    parser.add_argument("--print-formal-allocation-indices", action="store_true", help="Print the canonical hosted-worker matrix as compact JSON without launching a browser.")  # Let the workflow derive its complete matrix from exact-source catalog policy.
    parser.add_argument("--source-commit", default="", help="Exact 40-character commit expected by --aggregate-only.")  # Bind downloaded evidence to the workflow checkout.
    args = parser.parse_args()  # Parse caller options.
    if args.total_cycles < 1:  # Reject an empty test run.
        parser.error("--total-cycles must be at least 1")  # Require real UI work.
    if args.parallel < 1:  # Reject disabled concurrency.
        parser.error("--parallel must be at least 1")  # Preserve forward progress.
    if args.progress_every < 1:  # Reject an invalid progress divisor.
        parser.error("--progress-every must be at least 1")  # Preserve bounded monitoring.
    if args.roulette_replicas < 1:  # Reject a disabled Roulette allocation.
        parser.error("--roulette-replicas must be at least 1")  # Preserve complete game coverage.
    if args.game_replicas < 1:  # Reject disabled resumed game allocation.
        parser.error("--game-replicas must be at least 1")  # Preserve forward progress.
    if args.max_attempts_per_cycle < 1:  # Reject a retry policy that cannot attempt a cycle.
        parser.error("--max-attempts-per-cycle must be at least 1")  # Preserve real UI execution.
    if args.allocation_index is not None and args.allocation_index < 0:  # Reject negative distributed worker identities.
        parser.error("--allocation-index must be zero or greater")  # Require a deterministic allocation index.
    if sum((bool(args.aggregate_only), args.allocation_index is not None, bool(args.print_formal_allocation_indices))) > 1:  # Keep planner, worker, and aggregate roles mutually exclusive.
        parser.error("formal planner, worker, and aggregate modes cannot be combined")  # Prevent ambiguous distributed execution.
    if args.aggregate_only or args.allocation_index is not None or args.print_formal_allocation_indices:  # Enforce one immutable formal distributed plan.
        if args.total_cycles != 50_000 or args.only_games.strip() or args.replicate_games.strip() or args.roulette_replicas != 4 or args.resume_shards:  # Reject focused, resized, or resumed distributed variants.
            parser.error("distributed modes require exactly 50000 full-catalog cycles, four Roulette replicas, and no resume or extra replicas")  # Freeze issue-owned accounting.
    if args.aggregate_only and not args.source_commit.strip():  # Require explicit provenance for downloaded artifacts.
        parser.error("--aggregate-only requires --source-commit")  # Avoid inferring identity from mutable workflow context.
    return args  # Return validated options.


# Resolve and validate the selected catalog subset.
def selected_games(args):
    if not args.only_games.strip():  # Default to the complete installed catalog.
        return list(GAME_IDS)  # Preserve canonical order.
    requested = [item.strip() for item in args.only_games.split(",") if item.strip()]  # Parse explicit focused IDs.
    unknown = [game_id for game_id in requested if game_id not in GAME_IDS]  # Reject typos and stale catalog entries.
    if unknown:  # Fail before starting runtime resources.
        raise ValueError(f"unknown game IDs: {unknown}")  # Preserve actionable caller evidence.
    return requested  # Return the validated focused catalog order.


# Allocate exact deterministic quotas and contiguous global cycle ranges.
def allocate_cycles(game_ids, total_cycles, roulette_replicas, replicated_games, game_replicas, replica_policy=None):
    if total_cycles < len(game_ids):  # Require at least one real cycle per selected game.
        raise ValueError("total cycles must be at least the selected game count")  # Prevent silent zero-coverage games.
    base, remainder = divmod(total_cycles, len(game_ids))  # Divide evenly with a deterministic prefix remainder.
    allocations = []  # Preserve game, quota, and global offset together.
    offset = 0  # Start global IDs at zero.
    for index, game_id in enumerate(game_ids):  # Allocate every selected catalog game.
        quota = base + (1 if index < remainder else 0)  # Give the prefix one extra cycle until the remainder is exhausted.
        policy = (replica_policy or {}).get(game_id, {})  # Prefer the canonical formal profile when the distributed planner supplies one.
        requested_replicas = int(policy.get("replicas", roulette_replicas if game_id == "roulette" else game_replicas if game_id in replicated_games else 1))  # Resolve profiled or explicitly focused parallel ranges.
        replica_count = min(quota, requested_replicas)  # Never create an empty worker.
        first_minimum = int(policy.get("first_replica_minimum_cycles", 0))  # Preserve a profiled affinity range such as Roulette's one-hundred Rebet activations.
        remaining_quota = quota - first_minimum if first_minimum else quota  # Reserve only the explicit primary-shard affinity budget.
        remaining_replicas = replica_count - 1 if first_minimum else replica_count  # Divide every non-affinity range evenly.
        if remaining_replicas < 1 or remaining_quota < remaining_replicas:  # Reject a stale profile that would create an empty worker.
            raise ValueError(f"replica policy cannot allocate nonempty ranges for {game_id}")
        replica_base, replica_remainder = divmod(remaining_quota, remaining_replicas)  # Divide the unreserved quota without dropping cycles.
        replica_quotas = ([first_minimum] if first_minimum else []) + [replica_base + (1 if index < replica_remainder else 0) for index in range(remaining_replicas)]  # Keep primary affinity first and every remaining range balanced.
        for replica_index, replica_quota in enumerate(replica_quotas):  # Allocate each independent browser/account/runtime worker.
            allocations.append((game_id, GAME_IDS.index(game_id), replica_index, replica_quota, offset))  # Bind game, replica, quota, and contiguous range.
            offset += replica_quota  # Advance to the next unique global cycle ID.
    if offset != total_cycles:  # Defend exact accounting before browser work.
        raise AssertionError("cycle allocation did not equal requested total")  # Preserve the arithmetic gate.
    return allocations  # Return deterministic shard work.


# Derive the exact profile-sized hosted allocation plan and reject stale catalog or strategy metadata. (TEST-092)
def formal_allocations():
    policy = formal_replica_policy(GAME_IDS, UI_STRATEGY_FAMILIES)  # Validate canonical provenance and duration sizing before allocating any cycle.
    return allocate_cycles(list(GAME_IDS), 50_000, 4, set(), 4, policy)  # Preserve exact global IDs while applying only checked-in per-game replica counts.


# Derive every hosted worker index from the exact-source catalog allocation policy. (TEST-092)
def formal_allocation_indices():
    allocations = formal_allocations()  # Reuse the validated exact-run duration profile and complete full-catalog contract.
    return list(range(len(allocations)))  # Return one contiguous unique matrix entry for every canonical allocation.


# Convert a timeout-cancelled shard into one aggregate-safe failure record.
async def run_bounded_shard(playwright, semaphore, args, allocation, run_id, source_commit):
    game_id, game_index, replica_index, quota, cycle_start = allocation  # Unpack the deterministic shard assignment.
    heartbeat_task = None  # Local/focused runs retain their existing monitoring and unlimited controller behavior.
    try:  # Bound each game without stranding its cleanup finally block.
        if args.allocation_index is not None:  # Give a stale formal profile a bounded cleanup window before the workflow's hard job timeout.
            heartbeat_task = asyncio.create_task(formal_worker_heartbeat(args.allocation_index, allocation))  # Keep hosted liveness visible even when no cycle reaches the count-based interval.
            async with asyncio.timeout(FORMAL_EXECUTION_BUDGET_SECONDS):
                return await run_game_shard(playwright, semaphore, args, game_id, game_index, replica_index, quota, cycle_start, run_id, source_commit)  # Execute one exact-source isolated shard inside the profile-staleness budget.
        return await run_game_shard(playwright, semaphore, args, game_id, game_index, replica_index, quota, cycle_start, run_id, source_commit)  # Preserve focused/local behavior without the hosted worker deadline.
    except Exception as exc:  # Preserve unexpected controller-level failures.
        return {"game": game_id, "game_index": game_index, "replica_index": replica_index, "quota": quota, "global_cycle_start": cycle_start, "global_cycle_end": cycle_start + quota - 1, "source_commit": source_commit, "attempted": 0, "attempted_actions": 0, "completed": 0, "failed": quota, "failed_attempts": quota, "status": "FAIL", "controller_error": safe_error(exc), "listener_cleanup": {"closed": False}, "control_seen_counts": {}, "control_activated_counts": {}, "failure_counts": {safe_error(exc): quota}, "browser_diagnostics": {"console_errors": {}, "page_errors": {}, "http_failures": {}}}  # Return a fully accounted exact-source fail-closed record.
    finally:  # Never leave the independent liveness task pending after success, failure, or timeout.
        await stop_formal_worker_heartbeat(heartbeat_task)  # Stop cadence output before the terminal worker line and artifact upload.


# Reuse only complete compatible worker handbacks from an earlier bounded controller run.
def partition_resume_allocations(args, allocations, source_commit):
    if not args.resume_shards:  # Default to a fresh run when resumption was not requested.
        return [], allocations  # Schedule every deterministic allocation.
    root = Path(args.shard_report_root).expanduser().resolve()  # Resolve the caller-selected terminal report root.
    resumed = []  # Retain only fully verified compatible reports.
    pending = []  # Schedule missing or incompatible allocations from scratch.
    for allocation in allocations:  # Inspect each deterministic game/replica range.
        game_id, game_index, replica_index, quota, cycle_start = allocation  # Unpack the expected identity and range.
        path = root / f"{game_index:02d}-{game_id}-r{replica_index}.json"  # Resolve the worker's terminal filename.
        if not path.exists():  # Treat absent reports as unfinished work.
            pending.append(allocation)  # Schedule the complete assigned range.
            continue  # Inspect the next allocation.
        try:  # Reject corrupt or partial evidence without aborting safe resumption.
            report = json.loads(path.read_text(encoding="utf-8"))  # Read the candidate terminal report.
        except Exception:  # Treat unreadable JSON as incomplete evidence.
            pending.append(allocation)  # Rerun the complete assigned range.
            continue  # Inspect the next allocation.
        compatible = report.get("source_commit") == source_commit and report.get("game") == game_id and report.get("game_index") == game_index and report.get("replica_index") == replica_index and report.get("quota") == quota and report.get("global_cycle_start") == cycle_start and report.get("global_cycle_end") == cycle_start + quota - 1  # Require exact source and deterministic assignment identity.
        terminal = report.get("attempted") == quota and report.get("listener_cleanup", {}).get("closed") is True and report.get("isolation", {}).get("player_match") and report.get("isolation", {}).get("nonnegative_balance")  # Require full attempts, cleanup, and account isolation.
        if compatible and terminal:  # Reuse only a complete safe-boundary handback.
            resumed.append(report)  # Preserve its failures as formal evidence.
        else:  # Rerun incomplete or incompatible work from its full range.
            pending.append(allocation)  # Schedule one fresh isolated worker.
    return resumed, pending  # Return immutable evidence and remaining work separately.


# Load one and only one exact-source report for every deterministic distributed allocation.
def load_distributed_shards(args, allocations, source_commit):
    root = Path(args.shard_report_root).expanduser().resolve()  # Resolve the merged GitHub artifact directory.
    evidence_root = Path(args.evidence_root).expanduser().resolve()  # Resolve the downloaded visual-evidence directory.
    expected_names = {f"{game_index:02d}-{game_id}-r{replica_index}.json" for game_id, game_index, replica_index, _quota, _cycle_start in allocations}  # Derive the complete immutable filename inventory.
    actual_names = {path.name for path in root.glob("*.json")} if root.is_dir() else set()  # Inventory only terminal shard JSON files.
    if actual_names != expected_names:  # Reject missing, extra, or colliding worker artifacts.
        raise RuntimeError(f"distributed shard inventory mismatch expected={len(expected_names)} actual={len(actual_names)}")  # Report bounded counts without private paths.
    results = []  # Preserve canonical allocation order in the terminal aggregate.
    referenced_artifacts = set()  # Prevent duplicate screenshot references from satisfying multiple viewport rows.
    for allocation in allocations:  # Validate every expected report against its immutable assignment.
        game_id, game_index, replica_index, quota, cycle_start = allocation  # Unpack the canonical worker identity and range.
        path = root / f"{game_index:02d}-{game_id}-r{replica_index}.json"  # Resolve the expected terminal report.
        try:  # Convert malformed or partial JSON into a fail-closed controller result.
            report = json.loads(path.read_text(encoding="utf-8"))  # Read only the downloaded public evidence.
        except Exception as exc:  # Reject corrupt worker handbacks without launching replacement work.
            raise RuntimeError(f"distributed shard JSON is unreadable for allocation {game_index}:{replica_index}") from exc  # Name only the public deterministic index.
        compatible = report.get("source_commit") == source_commit and report.get("game") == game_id and report.get("game_index") == game_index and report.get("replica_index") == replica_index and report.get("quota") == quota and report.get("global_cycle_start") == cycle_start and report.get("global_cycle_end") == cycle_start + quota - 1 and report.get("requirements") == list(REQUIREMENT_IDS)  # Require exact source, range, identity, and requirement mapping.
        if not compatible:  # Reject foreign-source or incorrectly assigned evidence.
            raise RuntimeError(f"distributed shard identity mismatch for allocation {game_index}:{replica_index}")  # Keep the diagnostic sanitized and deterministic.
        for visual in report.get("visuals", []):  # Verify every claimed screenshot is present in the downloaded corpus.
            artifact_name = str(visual.get("artifact", ""))  # Read the worker-authored repository-relative evidence name.
            artifact_path = Path(artifact_name)  # Parse the portable relative screenshot path.
            if not artifact_name or artifact_path.is_absolute() or ".." in artifact_path.parts or "\\" in artifact_name or artifact_path.suffix.lower() != ".png":  # Reject private, escaping, nonportable, or non-PNG references.
                raise RuntimeError(f"distributed visual reference is invalid for allocation {game_index}:{replica_index}")  # Keep the failure bound to the public allocation.
            normalized_artifact = artifact_path.as_posix()  # Normalize the portable artifact identity.
            if normalized_artifact in referenced_artifacts:  # Reject one screenshot reused for multiple governed rows.
                raise RuntimeError(f"distributed visual reference is duplicated for allocation {game_index}:{replica_index}")  # Preserve a bounded deterministic diagnostic.
            if not (evidence_root / artifact_path).is_file():  # Require the named screenshot to have survived artifact upload and download.
                raise RuntimeError(f"distributed visual artifact is missing for allocation {game_index}:{replica_index}")  # Fail before claiming visual completeness.
            referenced_artifacts.add(normalized_artifact)  # Reserve the verified screenshot identity exactly once.
        results.append(report)  # Add the exact compatible shard, including honest failures, for aggregate accounting.
    return results  # Return the complete ordered shard corpus.


# Execute bounded game shards and build one terminal qualification report.
async def run_all(args):
    game_ids = selected_games(args)  # Resolve the complete or focused catalog subset.
    source_commit = resolve_distributed_source_commit(args.source_commit) if args.aggregate_only else resolve_source_commit()  # Freeze either distributed or clean-checkout provenance before accepting evidence.
    replicated_games = {item.strip() for item in args.replicate_games.split(",") if item.strip()}  # Parse explicit additional replica targets.
    unknown_replicas = replicated_games.difference(game_ids)  # Reject out-of-scope or misspelled replica targets.
    if unknown_replicas:  # Fail before starting local resources.
        raise ValueError(f"replicate-games not selected: {sorted(unknown_replicas)}")  # Preserve an actionable caller error.
    formal_distributed = args.aggregate_only or args.allocation_index is not None  # Keep planner-owned profile sizing exclusive to immutable distributed roles.
    allocations = formal_allocations() if formal_distributed else allocate_cycles(game_ids, args.total_cycles, args.roulette_replicas, replicated_games, args.game_replicas)  # Allocate exact quotas, replicas, and global IDs.
    if args.aggregate_only:  # Load the immutable downloaded corpus without importing or launching Playwright.
        resumed_results = load_distributed_shards(args, allocations, source_commit)  # Require all exact reports before aggregate accounting.
        pending_allocations = []  # Never repair missing remote work inside the aggregate job.
    elif args.allocation_index is not None:  # Run exactly one formal deterministic assignment on this hosted worker.
        if args.allocation_index >= len(allocations):  # Reject stale workflow matrices when the catalog changes.
            raise ValueError(f"allocation index out of range for {len(allocations)} formal workers")  # Preserve the exact expected matrix size.
        resumed_results = []  # Distributed workers never reuse an earlier run.
        pending_allocations = [allocations[args.allocation_index]]  # Schedule only the caller-owned immutable range.
    else:  # Preserve the existing bounded single-controller mode for focused development.
        resumed_results, pending_allocations = partition_resume_allocations(args, allocations, source_commit)  # Reuse only exact-source compatible safe-boundary handbacks.
    run_id = f"{int(time.time())}-{os.getpid()}"  # Create a collision-resistant local-only runtime identity.
    report = {"status": "FAIL", "requested_cycles": args.total_cycles, "selected_games": game_ids, "selected_game_count": len(game_ids), "registered_game_count": len(GAME_IDS), "worker_count": len(allocations), "resumed_worker_count": len(resumed_results), "pending_worker_count": len(pending_allocations), "roulette_replicas": args.roulette_replicas if "roulette" in game_ids else 0, "replicated_games": sorted(replicated_games), "parallel_limit": args.parallel, "source_commit": source_commit, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "requirements": list(REQUIREMENT_IDS)}  # Start the exact-source aggregate artifact fail closed.
    fresh_results = []  # Keep aggregate-only mode browser-free.
    if pending_allocations:  # Import and launch Playwright only when this process owns real browser work.
        from playwright.async_api import async_playwright  # Load Playwright only for explicit worker execution.

        semaphore = asyncio.Semaphore(args.parallel)  # Bound active browsers, servers, and disposable runtimes.
        async with async_playwright() as playwright:  # Own the shared Playwright driver lifecycle.
            tasks = [asyncio.create_task(run_bounded_shard(playwright, semaphore, args, allocation, run_id, source_commit)) for allocation in pending_allocations]  # Queue only caller-owned deterministic workers.
            fresh_results = await asyncio.gather(*tasks)  # Wait for every newly terminal shard handback.
    results = resumed_results + fresh_results  # Combine earlier safe boundaries with fresh terminal evidence.
    if args.allocation_index is not None:  # Return one hosted worker's honest terminal result without pretending it is the aggregate.
        worker_result = results[0]  # Resolve the single exact allocation result.
        worker_report = {"status": worker_result.get("status", "FAIL"), "allocation_index": args.allocation_index, "formal_worker_count": len(allocations), "source_commit": source_commit, "requirements": list(REQUIREMENT_IDS), "shard": worker_result}  # Bind the worker controller handback to the full immutable plan.
        write_json(Path(args.report).expanduser().resolve(), worker_report)  # Preserve a concise worker-level artifact beside the shard evidence.
        print(f"UI50000 WORKER {worker_report['status']} allocation={args.allocation_index}/{len(allocations)} attempted={worker_result.get('attempted', 0)} completed={worker_result.get('completed', 0)}", flush=True)  # Emit bounded monitoring without private paths.
        return 0 if worker_report["status"] == "PASS" else 1  # Fail the hosted worker when its assigned range fails.
    seen_counts = Counter()  # Aggregate discovered control states.
    activated_counts = Counter()  # Aggregate real DOM activations.
    failure_counts = Counter()  # Aggregate product/harness failure classes.
    console_errors = Counter()  # Aggregate browser console errors.
    page_errors = Counter()  # Aggregate uncaught JavaScript errors.
    http_failures = Counter()  # Aggregate failed browser API requests.
    for result in results:  # Merge every terminal game artifact.
        seen_counts.update(result.get("control_seen_counts", {}))  # Merge discovered controls.
        activated_counts.update(result.get("control_activated_counts", {}))  # Merge successful activations.
        failure_counts.update(result.get("failure_counts", {}))  # Merge failed cycle classes.
        diagnostics = result.get("browser_diagnostics", {})  # Read grouped browser signals.
        console_errors.update(diagnostics.get("console_errors", {}))  # Merge console errors.
        page_errors.update(diagnostics.get("page_errors", {}))  # Merge uncaught page errors.
        http_failures.update(diagnostics.get("http_failures", {}))  # Merge protected-request failures.
    assigned_ids = []  # Verify global range uniqueness without retaining per-cycle payloads.
    for result in results:  # Reconstruct each deterministic assigned range.
        assigned_ids.extend(range(result["global_cycle_start"], result["global_cycle_end"] + 1))  # Add assigned IDs for overlap/gap checks.
    unique_ids = set(assigned_ids)  # Deduplicate the reconstructed assignment.
    expected_ids = set(range(args.total_cycles))  # Build the exact requested global ID set.
    control_coverage = classify_control_coverage(seen_counts, activated_counts, selected_games=set(game_ids))  # Scope only registered-game navigation outside an explicit focused selection while preserving all selected and full-catalog floors.
    failed_controls = control_coverage["failed"]  # Keep the red eligible-control evidence explicit for the aggregate gate.
    game_counts = {}  # Aggregate replicated workers back into canonical game outcomes.
    for result in sorted(results, key=lambda item: (item["game_index"], item.get("replica_index", 0))):  # Preserve game and replica order.
        item = game_counts.setdefault(result["game"], {"quota": 0, "attempted": 0, "attempted_actions": 0, "completed": 0, "failed": 0, "failed_attempts": 0, "status": "PASS", "worker_latencies": []})  # Start one canonical game record.
        item["quota"] += result["quota"]  # Sum the exact assigned game quota.
        item["attempted"] += result.get("attempted", 0)  # Sum real browser attempts across replicas.
        item["attempted_actions"] += result.get("attempted_actions", 0)  # Sum retry-inclusive UI actions across replicas.
        item["completed"] += result.get("completed", 0)  # Sum terminal completed plays across replicas.
        item["failed"] += result.get("failed", 0)  # Sum failed plays across replicas.
        item["failed_attempts"] += result.get("failed_attempts", 0)  # Sum retry-level failures across replicas.
        item["status"] = "FAIL" if result.get("status", "FAIL") != "PASS" else item["status"]  # Fail the game if any worker fails.
        item["worker_latencies"].append(result.get("latency", {}))  # Preserve each independent worker's timing summary.
    visual_failures = []  # Collect geometry failures across distributed governed viewports.
    expected_viewports = {viewport["id"] for viewport in VIEWPORTS}  # Freeze the complete governed viewport identity set.
    visuals_complete = True  # Keep missing, duplicate, or recovered-failure evidence fail closed.
    for result in results:  # Inspect each shard's complete visual handback.
        visuals = result.get("visuals", [])  # Read this worker's representative evidence inventory.
        viewport_ids = [visual.get("viewport", {}).get("id") for visual in visuals]  # Extract stable viewport identities.
        if len(visuals) != len(VIEWPORTS) or set(viewport_ids) != expected_viewports or len(viewport_ids) != len(set(viewport_ids)) or any(visual.get("evidence_class") != "after_pass" or not visual.get("artifact") for visual in visuals):  # Require one passing artifact for every governed viewport.
            visuals_complete = False  # Reject absent, duplicate, recovered-failure, or unnamed evidence.
        for visual in visuals:  # Evaluate every governed viewport independently.
            geometry = visual.get("geometry", {})  # Read automated geometry evidence when available.
            if geometry.get("document_overflow_x_px", 0) > 0 or geometry.get("brand_truncated") or geometry.get("clipped_enabled_control_count", 0) > 0 or geometry.get("occluded_enabled_control_count", 0) > 0 or geometry.get("essential_stage_failures"):  # Detect governed overflow, clipping, branding, overlays, and incomplete non-control stages.
                visual_failures.append({"game": result["game"], "viewport": visual.get("viewport", {}), "geometry": geometry})  # Preserve sanitized defect evidence.
    attempted = sum(result.get("attempted", 0) for result in results)  # Count actual browser test attempts.
    attempted_actions = sum(result.get("attempted_actions", 0) for result in results)  # Count retry-inclusive rendered UI actions.
    completed = sum(result.get("completed", 0) for result in results)  # Count terminal successful UI cycles.
    failed = sum(result.get("failed", 0) for result in results)  # Count failed or uncompleted cycles.
    failed_attempts = sum(result.get("failed_attempts", 0) for result in results)  # Count every failed rendered UI attempt.
    cleanup_ok = all(result.get("listener_cleanup", {}).get("closed") is True for result in results)  # Require every tracked listener to close.
    isolation_ok = all(result.get("isolation", {}).get("player_match") and result.get("isolation", {}).get("nonnegative_balance") for result in results)  # Require canonical user isolation.
    shards_pass = len(results) == len(allocations) and all(result.get("status") == "PASS" for result in results)  # Require every deterministic worker to report an explicit passing terminal state.
    ranges_ok = len(assigned_ids) == args.total_cycles and len(unique_ids) == args.total_cycles and unique_ids == expected_ids  # Require no duplicate or missing global IDs.
    control_coverage.update({"discovered_signatures": len(seen_counts), "activated_signatures": len(activated_counts), "minimum_required_activations": CONTROL_ACTIVATION_FLOOR, "activated_counts": dict(sorted(activated_counts.items()))})  # Add aggregate inventory totals to the complete classifications.
    report.update({"attempted_cycles": attempted, "attempted_actions": attempted_actions, "completed_cycles": completed, "failed_cycles": failed, "failed_attempts": failed_attempts, "assignment": {"range_count": len(assigned_ids), "unique_count": len(unique_ids), "no_gaps_or_duplicates": ranges_ok}, "game_counts": game_counts, "control_coverage": control_coverage, "failure_counts": dict(failure_counts.most_common()), "browser_diagnostics": {"console_errors": dict(console_errors.most_common()), "page_errors": dict(page_errors.most_common()), "http_failures": dict(http_failures.most_common())}, "visual_failures": visual_failures, "visuals_complete": visuals_complete, "shards_pass": shards_pass, "isolation_ok": isolation_ok, "listener_cleanup_ok": cleanup_ok, "shards": results})  # Store complete aggregate evidence.
    full_catalog = not args.only_games.strip() and len(game_ids) == len(GAME_IDS)  # Detect the formal full-catalog command.
    minimum_game_cycles = min((item["completed"] for item in game_counts.values()), default=0)  # Record the successful per-game floor.
    report["minimum_completed_per_game"] = minimum_game_cycles  # Preserve distribution evidence.
    classification_complete = control_coverage["classified_count"] == len(set(seen_counts).union(activated_counts))  # Prove every observed identity has exactly one class.
    gates = [attempted == args.total_cycles, completed == args.total_cycles, failed == 0, ranges_ok, cleanup_ok, isolation_ok, shards_pass, visuals_complete, not failure_counts, not console_errors, not page_errors, not http_failures, not visual_failures, classification_complete, not failed_controls]  # Evaluate every universal qualification gate.
    if full_catalog:  # Enforce the formal #227 per-game floor only on the complete command.
        gates.append(minimum_game_cycles >= args.total_cycles // len(GAME_IDS))  # Require the deterministic minimum allocation.
    report["status"] = "PASS" if all(gates) else "FAIL"  # Mark the aggregate only after every gate passes.
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())  # Record terminal report time.
    write_json(Path(args.report).expanduser().resolve(), report)  # Persist the aggregate machine-readable artifact.
    print(f"UI50000 {report['status']} assigned={attempted} actions={attempted_actions} completed={completed} uncompleted={failed} failed_attempts={failed_attempts} games={len(game_ids)} failed_controls={len(failed_controls)} report={Path(args.report).expanduser().resolve()}", flush=True)  # Emit one concise terminal handback.
    return 0 if report["status"] == "PASS" else 1  # Return the release qualification status.


# Run the command-line entry point without import-time side effects.
def main():
    args = parse_args()  # Read the requested cycle volume and runtime bounds.
    try:  # Convert caller/configuration failures into a nonzero terminal result.
        if args.print_formal_allocation_indices:  # Keep workflow planning browser-free and exact-source deterministic.
            print(json.dumps(formal_allocation_indices(), separators=(",", ":")), flush=True)  # Emit compact GitHub-matrix JSON without logs or mutable metadata.
            return 0  # Finish before importing or launching Playwright.
        return asyncio.run(run_all(args))  # Execute the complete browser qualification.
    except Exception as exc:  # Preserve one concise controller failure.
        print(f"UI50000 FAIL controller={safe_error(exc)}", flush=True)  # Exclude credentials, sessions, and raw logs.
        return 1  # Fail closed.


# Enter only when launched as the UI qualification command.
if __name__ == "__main__":
    raise SystemExit(main())  # Exit with the aggregate qualification status.
