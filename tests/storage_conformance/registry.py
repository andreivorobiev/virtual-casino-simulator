# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider harness registry for the unchanged A-J suite. (STORAGE-025, TEST-257)"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from tests.storage_conformance.database_harnesses import MySQLHarness, PostgresHarness
from tests.storage_conformance.harness import JsonHarness, ProviderHarness


@dataclass(frozen=True)
class HarnessRegistration:
    """Bind a stable provider label to its isolated harness constructor."""

    name: str
    factory: Callable[[], ProviderHarness]


# Keep every provider registered while each database harness owns its reviewed reachability skip.
REGISTRATIONS = (
    HarnessRegistration(name="json", factory=JsonHarness),
    HarnessRegistration(name="mysql", factory=MySQLHarness),
    HarnessRegistration(name="postgres", factory=PostgresHarness),
)


def registered_harnesses() -> tuple[HarnessRegistration, ...]:
    """Return the immutable registration inventory in deterministic order."""

    return REGISTRATIONS
