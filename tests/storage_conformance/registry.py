# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider harness registry for the unchanged A-J suite. (STORAGE-025, TEST-257)"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from tests.storage_conformance.harness import JsonHarness, ProviderHarness


@dataclass(frozen=True)
class HarnessRegistration:
    """Bind a stable provider label to its isolated harness constructor."""

    name: str
    factory: Callable[[], ProviderHarness]


# Early Phase-A authoring registers JSON only; database registrations join unchanged after #1059.
REGISTRATIONS = (HarnessRegistration(name="json", factory=JsonHarness),)


def registered_harnesses() -> tuple[HarnessRegistration, ...]:
    """Return the immutable registration inventory in deterministic order."""

    return REGISTRATIONS
