# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Opaque identifier generation for repository entities and game actions.
import secrets

# Define the new_id function used by this module.
def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"
