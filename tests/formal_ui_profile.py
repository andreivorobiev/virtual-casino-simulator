#!/usr/bin/env python3
# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Validate the canonical TEST-092 duration profile and derive bounded replicas."""

import json  # Read the checked-in exact-run timing evidence without executable configuration.
import math  # Convert conservative profiled duration into a deterministic worker count.
from pathlib import Path  # Resolve the profile beside its sole planner owner.


PROFILE_PATH = Path(__file__).with_name("formal_ui_duration_profile.json")


# Load the immutable planning policy once so planner, worker, and aggregate use one byte-identical source.
def load_profile(path=PROFILE_PATH):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("formal UI duration profile is unreadable") from exc
    if payload.get("schema_version") != 1 or payload.get("requirement") != "TEST-092":
        raise RuntimeError("formal UI duration profile identity is invalid")
    policy = payload.get("policy", {})
    ordered_limits = [policy.get(name) for name in ("planning_target_seconds", "execution_budget_seconds", "ui_step_target_seconds")]
    if not all(isinstance(value, int) and value > 0 for value in ordered_limits) or ordered_limits != sorted(ordered_limits) or len(set(ordered_limits)) != len(ordered_limits):
        raise RuntimeError("formal UI duration budgets are invalid")
    hard_seconds = int(policy.get("hard_job_timeout_minutes", 0)) * 60
    if hard_seconds <= ordered_limits[-1] or policy.get("max_matrix_workers") != 256:
        raise RuntimeError("formal UI hard worker policy is invalid")
    return payload


FORMAL_DURATION_PROFILE = load_profile()
FORMAL_PLANNING_TARGET_SECONDS = FORMAL_DURATION_PROFILE["policy"]["planning_target_seconds"]
FORMAL_EXECUTION_BUDGET_SECONDS = FORMAL_DURATION_PROFILE["policy"]["execution_budget_seconds"]
FORMAL_UI_STEP_TARGET_SECONDS = FORMAL_DURATION_PROFILE["policy"]["ui_step_target_seconds"]
FORMAL_WORKER_TIMEOUT_MINUTES = FORMAL_DURATION_PROFILE["policy"]["hard_job_timeout_minutes"]


# Reject catalog, strategy, provenance, or budget drift before GitHub creates a partial matrix. (TEST-092)
def formal_replica_policy(game_ids, strategy_families, profile=FORMAL_DURATION_PROFILE):
    entries = profile.get("games", [])
    profile_ids = [entry.get("id") for entry in entries]
    if profile_ids != list(game_ids) or len(profile_ids) != len(set(profile_ids)):
        raise RuntimeError("formal UI duration profile is stale for the catalog")
    source = profile.get("source", {})
    source_commit = str(source.get("commit", ""))
    run_id = source.get("run_id")
    if not isinstance(run_id, int) or run_id < 1 or not str(source.get("run_url", "")).endswith(f"/actions/runs/{run_id}") or len(source_commit) != 40 or any(character not in "0123456789abcdef" for character in source_commit):
        raise RuntimeError("formal UI duration profile provenance is invalid")
    planning_target = int(profile["policy"]["planning_target_seconds"])
    ui_target = int(profile["policy"]["ui_step_target_seconds"])
    policies = {}
    total_workers = 0
    for entry in entries:
        game_id = entry["id"]
        if entry.get("strategy_family") != strategy_families.get(game_id):
            raise RuntimeError(f"formal UI duration profile strategy is stale for {game_id}")
        measured_cycles = entry.get("measured_cycles")
        observed_seconds = entry.get("observed_ui_seconds")
        planning_seconds = entry.get("planning_ui_seconds")
        if not all(isinstance(value, int) and value > 0 for value in (measured_cycles, observed_seconds, planning_seconds)) or planning_seconds < observed_seconds:
            raise RuntimeError(f"formal UI duration profile timing is invalid for {game_id}")
        replica_count = math.ceil(planning_seconds / planning_target)
        while math.ceil(planning_seconds * math.ceil(measured_cycles / replica_count) / measured_cycles) > planning_target:
            replica_count += 1  # Account for the largest integer range instead of accepting an average-only target.
        first_replica_minimum = int(entry.get("first_replica_minimum_cycles", 0))
        if replica_count > measured_cycles or first_replica_minimum < 0 or first_replica_minimum > measured_cycles:
            raise RuntimeError(f"formal UI duration profile allocation is invalid for {game_id}")
        if first_replica_minimum and math.ceil(planning_seconds * first_replica_minimum / measured_cycles) > ui_target:
            raise RuntimeError(f"formal UI affinity range exceeds the UI target for {game_id}")
        policies[game_id] = {"replicas": replica_count, "first_replica_minimum_cycles": first_replica_minimum}
        total_workers += replica_count
    if total_workers > int(profile["policy"]["max_matrix_workers"]):
        raise RuntimeError("formal UI duration profile exceeds the GitHub matrix limit")
    return policies
