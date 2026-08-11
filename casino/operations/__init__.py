# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Sanitized liveness, readiness, and heartbeat foundation for issue #72."""

# Export the isolated route registrar for the later shared-router integration.
from casino.operations.api import register
# Export the probe service so focused tests and future Admin integration share one state model.
from casino.operations.service import OperationsProbeService

# Declare the intended public surface without exporting probe implementation helpers accidentally.
__all__ = ["OperationsProbeService", "register"]
