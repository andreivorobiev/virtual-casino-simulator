# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Execute the registered storage contract and enforce provider timing/cleanup. (TEST-257)"""

from __future__ import annotations

import time
import unittest
from unittest import mock

from tests.storage_conformance.cases import CaseContext, GROUPS
from tests.storage_conformance.harness import JsonHarness, ProviderHarness
from tests.storage_conformance.registry import registered_harnesses


class _LifecycleFailure(RuntimeError):
    """Carry exact adversarial create and destroy failure identities."""


class _CreateFailureProvider:
    """Fail readiness only after the JSON harness allocates its owned root."""

    def __init__(self, failure: BaseException) -> None:
        self.failure = failure

    def ensure_ready(self) -> None:
        """Raise the exact injected create failure."""

        raise self.failure


class _DestroyFailingJsonHarness(JsonHarness):
    """Clean the owned root and then simulate a distinct destroy failure."""

    def __init__(self, failure: BaseException) -> None:
        super().__init__()
        self.failure = failure

    def destroy(self) -> None:
        """Complete real cleanup before raising the injected destroy failure."""

        super().destroy()
        raise self.failure


def _run_harness_contract(harness: ProviderHarness) -> tuple[float, object]:
    """Run one protected lifecycle while preserving any original create/case error."""

    started = time.perf_counter()
    root = getattr(harness, "root", None)
    try:
        provider = harness.create()
        root = getattr(harness, "root", root)
        for group in GROUPS:
            provider = harness.reset_fast()
            group_started = time.perf_counter()
            try:
                group.run(CaseContext(provider=provider, supports_true_concurrency=harness.supports_true_concurrency))
            except BaseException:
                group_elapsed = time.perf_counter() - group_started
                print(f"STORAGE-CONFORMANCE provider={harness.name} group={group.identifier}:{group.label} status=FAIL elapsed={group_elapsed:.3f}s", flush=True)
                raise
            group_elapsed = time.perf_counter() - group_started
            print(f"STORAGE-CONFORMANCE provider={harness.name} group={group.identifier}:{group.label} status=PASS elapsed={group_elapsed:.3f}s", flush=True)
    except BaseException:
        root = getattr(harness, "root", root)
        try:
            harness.destroy()
        except BaseException:
            # Cleanup is best-effort only when a create/case failure already owns the traceback.
            pass
        raise
    else:
        root = getattr(harness, "root", root)
        harness.destroy()
    return time.perf_counter() - started, root


class RegisteredStorageConformanceTests(unittest.TestCase):
    """Run every A-J group unchanged against each currently registered harness."""

    def test_registered_provider_contracts(self) -> None:
        """Require isolation, group timing evidence, hard budgets, and cleanup."""

        registrations = registered_harnesses()
        self.assertTrue(registrations, "storage conformance registry must not be empty")
        for registration in registrations:
            with self.subTest(provider=registration.name):
                harness = registration.factory()
                unavailable_reason = harness.unavailable_reason()
                if unavailable_reason is not None:
                    print(f"STORAGE-CONFORMANCE provider={harness.name} status=SKIP reason=reachability_absent", flush=True)
                    self.skipTest(unavailable_reason)
                elapsed, root = _run_harness_contract(harness)
                print(f"STORAGE-CONFORMANCE provider={harness.name} status=PASS elapsed={elapsed:.3f}s budget={harness.budget_seconds:.3f}s", flush=True)
                self.assertLess(elapsed, harness.budget_seconds, f"{harness.name} conformance exceeded its hard budget")
                if root is not None:
                    self.assertFalse(root.exists(), "successful harness run left disposable state behind")

    def test_partial_create_is_cleaned_without_masking_original_failure(self) -> None:
        """Require cleanup after partial create even when destroy also raises."""

        create_failure = _LifecycleFailure("create failure")
        destroy_failure = _LifecycleFailure("destroy failure")
        harness = _DestroyFailingJsonHarness(destroy_failure)
        with mock.patch("tests.storage_conformance.harness.storage_facade.JsonStorageProvider", return_value=_CreateFailureProvider(create_failure)):
            try:
                _run_harness_contract(harness)
            except _LifecycleFailure as observed:
                self.assertIs(create_failure, observed)
            else:
                self.fail("partial create unexpectedly succeeded")
        root = harness.root
        self.assertIsNotNone(root)
        self.assertFalse(root.exists(), "partial create left its disposable root behind")

    def test_json_harness_cleans_up_after_a_case_failure(self) -> None:
        """Prove the harness deletes its target when an unchanged case raises."""

        harness = JsonHarness()
        provider = harness.create()
        root = harness.root
        try:
            provider.write_document("conformance/cleanup/failure", {"residue": True})
            raise RuntimeError("synthetic case failure")
        except RuntimeError as error:
            self.assertEqual("synthetic case failure", str(error))
        finally:
            harness.destroy()
        self.assertIsNotNone(root)
        self.assertFalse(root.exists(), "failed harness run left disposable state behind")


if __name__ == "__main__":
    unittest.main()
