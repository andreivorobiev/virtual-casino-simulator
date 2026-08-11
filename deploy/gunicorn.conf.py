# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Loopback-only Gunicorn policy for the CORE-023 supervised service."""

# Import environment access for the non-secret listener port override used by isolated smoke tests.
import os

# Parse the bounded listener port while keeping the network interface fixed to IPv4 loopback.
listener_port = int(os.environ.get("CASINO_BIND_PORT", "8765"))
# Reject invalid ports before Gunicorn creates any listener.
if not 1 <= listener_port <= 65535:
    # Fail worker startup without printing any environment value beyond the public port number.
    raise RuntimeError("CASINO_BIND_PORT must be between 1 and 65535")

# Bind only to loopback so the edge proxy remains the sole future public listener.
bind = f"127.0.0.1:{listener_port}"
# Keep one process because the current persistence and capacity plan is single-process.
workers = 1
# Use Gunicorn's production threaded worker rather than Python's development HTTP server.
worker_class = "gthread"
# Permit two concurrent request threads within the single state-owning worker.
threads = 2
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
