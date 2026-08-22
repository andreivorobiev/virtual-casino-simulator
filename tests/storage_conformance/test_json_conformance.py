# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Execute the registered storage contract and enforce provider timing/cleanup. (TEST-257)"""

from __future__ import annotations

import time
import unittest

from tests.storage_conformance.cases import CaseContext, GROUPS
from tests.storage_conformance.harness import JsonHarness
from tests.storage_conformance.registry import registered_harnesses


class RegisteredStorageConformanceTests(unittest.TestCase):
    """Run every A-J group unchanged against each currently registered harness."""

    def test_registered_provider_contracts(self) -> None:
        """Require isolation, group timing evidence, hard budgets, and cleanup."""

        registrations = registered_harnesses()
        self.assertTrue(registrations, "storage conformance registry must not be empty")
        for registration in registrations:
            with self.subTest(provider=registration.name):
                harness = registration.factory()
                started = time.perf_counter()
                provider = harness.create()
                root = getattr(harness, "root", None)
                try:
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
                finally:
                    harness.destroy()
                elapsed = time.perf_counter() - started
                print(f"STORAGE-CONFORMANCE provider={harness.name} status=PASS elapsed={elapsed:.3f}s budget={harness.budget_seconds:.3f}s", flush=True)
                self.assertLess(elapsed, harness.budget_seconds, f"{harness.name} conformance exceeded its hard budget")
                if root is not None:
                    self.assertFalse(root.exists(), "successful harness run left disposable state behind")

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
