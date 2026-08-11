# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Canonical UTC timestamp formatting for durable records.
from datetime import datetime, timezone

# Define the utc_now function used by this module.
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

# Define the date_stamp function used by this module.
def date_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
