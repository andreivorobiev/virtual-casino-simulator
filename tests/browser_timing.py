# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed Browser wait-budget policy shared by every Playwright owner."""

# Read the optional CI/local override without coupling Browser cases to workflow code.
import os

# Name the sole supported Browser wait-budget override.
WAIT_MS_ENV = "CASINO_BROWSER_WAIT_MS"
# Preserve the historical five-second Browser wait budget when no override is supplied.
DEFAULT_WAIT_MS = 5000
# Reject impractically short waits that would turn scheduling jitter into false failures.
MIN_WAIT_MS = 100
# Bound caller-controlled waits so a typo cannot stall every Browser shard indefinitely.
MAX_WAIT_MS = 60_000
# Keep invalid override diagnostics fixed and free of caller-controlled values.
WAIT_MS_ERROR = "browser wait budget is invalid"


# Parse one decimal millisecond budget without accepting signs, whitespace, or coercible types.
def _configured_wait_ms():
    # Read the exact environment value or the reviewed local default.
    raw_value = os.environ.get(WAIT_MS_ENV, str(DEFAULT_WAIT_MS))
    # Require nonempty ASCII decimal digits before integer conversion.
    if not raw_value or not raw_value.isascii() or not raw_value.isdecimal():
        # Fail closed with one stable diagnostic.
        raise RuntimeError(WAIT_MS_ERROR)
    # Convert only the validated bounded decimal value.
    wait_ms = int(raw_value)
    # Reject values outside the reviewed Browser scheduling envelope.
    if not MIN_WAIT_MS <= wait_ms <= MAX_WAIT_MS:
        # Preserve the same value-free diagnostic for every invalid bound.
        raise RuntimeError(WAIT_MS_ERROR)
    # Return the safe millisecond budget consumed by Playwright waits.
    return wait_ms


# Resolve the one Browser wait knob once per test process.
WAIT_MS = _configured_wait_ms()
