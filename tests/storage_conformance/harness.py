# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Harness protocol and isolated JSON registration support. (STORAGE-025, TEST-257)"""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Protocol, runtime_checkable

from casino.core.storage.base import StorageProvider
from casino.core import storage as storage_facade


@runtime_checkable
class ProviderHarness(Protocol):
    """Create, reset, and destroy one isolated provider target."""

    name: str
    budget_seconds: float
    supports_true_concurrency: bool

    def create(self) -> StorageProvider:
        """Create a fresh isolated provider and return its public contract."""

    def reset_fast(self) -> StorageProvider:
        """Reset the retained target between unchanged conformance groups."""

    def destroy(self) -> None:
        """Destroy every synthetic byte owned by this harness."""


class JsonHarness:
    """Own one temporary-directory JSON provider without importing its module."""

    name = "json"
    budget_seconds = 10.0
    # JSON serializes durable mutations, but the unchanged suite still submits real threads.
    supports_true_concurrency = False

    def __init__(self) -> None:
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        self._root: Path | None = None
        self._provider: StorageProvider | None = None

    @property
    def root(self) -> Path | None:
        """Expose only the test-owned root for cleanup assertions."""

        return self._root

    def create(self) -> StorageProvider:
        """Create the provider through the public storage facade over an isolated root."""

        if self._temporary is not None:
            raise AssertionError("harness create must run exactly once")
        self._temporary = tempfile.TemporaryDirectory(prefix="storage-conformance-json-")
        self._root = Path(self._temporary.name).resolve()
        self._provider = storage_facade.JsonStorageProvider(self._root)
        self._provider.ensure_ready()
        return self._provider

    def reset_fast(self) -> StorageProvider:
        """Use the production reset boundary before each provider-neutral group."""

        if self._provider is None:
            raise AssertionError("harness reset requires a created provider")
        self._provider.reset()
        self._provider.ensure_ready()
        return self._provider

    def destroy(self) -> None:
        """Delete the complete temporary target and fail if any owned root remains."""

        root = self._root
        temporary = self._temporary
        self._provider = None
        self._temporary = None
        if temporary is not None:
            temporary.cleanup()
        if root is not None and root.exists():
            raise AssertionError("storage conformance harness left disposable state behind")
