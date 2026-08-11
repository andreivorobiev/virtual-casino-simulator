#!/usr/bin/env python3
# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Preserve the historical command while delegating to the file-header policy gate."""

from check_file_headers import main as check_file_headers


if __name__ == "__main__":
    raise SystemExit(check_file_headers(["--check"]))
