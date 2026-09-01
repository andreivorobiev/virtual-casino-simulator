# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Expose only the disabled route-free Challenge Points kernel. (#1091, CHALLENGE-003)"""

# Re-export only the immutable policy inputs and transition functions future adapters consume.
from casino.core.challenges.policy import (
    ACCEPTED,
    REJECTED,
    ChallengeDayState,
    ChallengeEvent,
    ChallengeReceipt,
    ChallengeRule,
    ChallengeScore,
    ChallengeTransition,
    complete_practice,
    complete_ranked,
    project_day,
    start_practice,
    start_ranked,
)

# Publish an explicit route-free surface rather than leaking implementation helpers.
__all__ = (
    "ACCEPTED",
    "REJECTED",
    "ChallengeDayState",
    "ChallengeEvent",
    "ChallengeReceipt",
    "ChallengeRule",
    "ChallengeScore",
    "ChallengeTransition",
    "complete_practice",
    "complete_ranked",
    "project_day",
    "start_practice",
    "start_ranked",
)
