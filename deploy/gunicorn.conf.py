# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Loopback-only Gunicorn policy for the CORE-023 supervised service."""

# Import environment access for the non-secret listener port override used by isolated smoke tests.
import os


# Parse one public integer control without reflecting a malformed environment value.
def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    # Read the scalar once so validation cannot observe different environment snapshots.
    raw_value = os.environ.get(name, str(default))
    # Convert only base-ten integer text inside a fixed diagnostic boundary.
    try:
        # Parse the configured value without logging or interpolating it.
        value = int(raw_value)
    # Collapse malformed text into the same value-free public range error.
    except (TypeError, ValueError):
        # Fail startup with only the reviewed configuration key and range.
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}") from None
    # Reject values outside the reviewed resource ceiling before process construction.
    if not minimum <= value <= maximum:
        # Keep the failure independent from caller-controlled configuration bytes.
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    # Return the validated integer to the declarative Gunicorn policy.
    return value


# Parse the bounded listener port while keeping the network interface fixed to IPv4 loopback.
listener_port = _bounded_int("CASINO_BIND_PORT", 8765, 1, 65535)

# Bind only to loopback so the edge proxy remains the sole future public listener.
bind = f"127.0.0.1:{listener_port}"
# Parse the explicit qualification and production worker count with one conservative process default.
workers = _bounded_int("CASINO_GUNICORN_WORKERS", 1, 1, 8)
# Use Gunicorn's production threaded worker rather than Python's development HTTP server.
worker_class = "gthread"
# Parse the per-worker request concurrency independently from the physical database ceiling.
threads = _bounded_int("CASINO_GUNICORN_THREADS", 16, 1, 64)
# Bound an unresponsive request before Gunicorn replaces the failed worker.
timeout = 30
# Allow in-flight requests a bounded graceful drain during stop or restart.
graceful_timeout = 20
# Retain short proxy connections without occupying a thread indefinitely.
keepalive = 5
# Keep the process attached to systemd supervision.
daemon = False
# Send access records to systemd's configured standard output stream.
accesslog = "-"
# Send lifecycle and failure diagnostics to systemd's configured error stream.
errorlog = "-"
# Capture application standard streams in the same supervised error stream.
capture_output = True
# Keep service diagnostics useful without enabling debug configuration output.
loglevel = "info"
