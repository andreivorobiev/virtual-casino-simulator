#!/usr/bin/env python3
# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Compatibility entrypoint for the extracted repository test runner."""

# Import interpreter path controls before loading the package-owned runner.
import sys
# Resolve the repository root for direct script execution from any working directory.
from pathlib import Path

# Resolve the repository root from the stable compatibility entrypoint location.
ROOT = Path(__file__).resolve().parents[1]
# Make the repository package importable when callers execute this file directly.
sys.path.insert(0, str(ROOT))

# Re-export the narrowly used compatibility helpers while the implementation lives in tests.runner.
from tests.runner import (  # noqa: E402
    DEFAULT_AUTH_EMAIL,
    DEFAULT_AUTH_PASSWORD,
    api,
    login_default_user,
    main,
    roulette_i18n_failure_diagnostic,
    start_server,
    stop_server,
)

# Preserve the historical CLI by delegating exactly once to the extracted runner.
if __name__ == "__main__":
    # Return the extracted runner's unchanged process status to every workflow and operator.
    raise SystemExit(main())
