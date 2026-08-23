# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Fail conformance-kit provider branches, direct imports, and case skips. (TEST-257)"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

from tests.storage_conformance.cases import GROUPS
from tests.storage_conformance.database_harnesses import MySQLHarness, PostgresHarness
from tests.storage_conformance.harness import JsonHarness, ProviderHarness
from tests.storage_conformance.registry import registered_harnesses


PACKAGE_ROOT = Path(__file__).resolve().parent
CONCRETE_MODULES = {
    "casino.core.storage.json_provider",
    "casino.core.storage.mysql_provider",
    "casino.core.storage.postgres_provider",
}
# Bind the public concrete class spellings so facade imports cannot evade the package gate.
CONCRETE_NAMES = {"JsonStorageProvider", "MySQLStorageProvider", "PostgresStorageProvider"}
CASE_PRODUCT_IMPORTS = {"casino.core.storage.base", "casino.errors"}


def _python_sources() -> list[Path]:
    """Return every first-party Python source in this conformance package."""

    return sorted(path for path in PACKAGE_ROOT.rglob("*.py") if "__pycache__" not in path.parts)


class StorageConformanceBoundaryTests(unittest.TestCase):
    """Keep cases provider-neutral and make future harness registration explicit."""

    def test_concrete_provider_modules_are_never_imported(self) -> None:
        """Reject direct concrete-module or concrete-class imports anywhere in the kit."""

        violations: list[str] = []
        for path in _python_sources():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in CONCRETE_MODULES or any(alias.name.startswith(f"{module}.") for module in CONCRETE_MODULES):
                            violations.append(f"{path.name}:{node.lineno}:{alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module in CONCRETE_MODULES or any(module.startswith(f"{candidate}.") for candidate in CONCRETE_MODULES):
                        violations.append(f"{path.name}:{node.lineno}:{module}")
                    for alias in node.names:
                        if alias.name in CONCRETE_NAMES:
                            violations.append(f"{path.name}:{node.lineno}:{module}.{alias.name}")
        self.assertEqual([], violations)

    def test_cases_have_only_provider_neutral_product_imports_and_no_skips(self) -> None:
        """Reject capability skips, provider-name branches, and product-layer imports in cases."""

        case_path = PACKAGE_ROOT / "cases.py"
        source = case_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(case_path))
        product_imports: set[str] = set()
        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("casino."):
                product_imports.add(node.module or "")
            elif isinstance(node, ast.Import):
                product_imports.update(alias.name for alias in node.names if alias.name.startswith("casino."))
            elif isinstance(node, ast.Call):
                function_name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ""
                if function_name.startswith("skip"):
                    violations.append(f"skip call at line {node.lineno}")
            elif isinstance(node, ast.Compare) and isinstance(node.left, ast.Attribute) and node.left.attr == "name":
                violations.append(f"provider-name comparison at line {node.lineno}")
        self.assertEqual(CASE_PRODUCT_IMPORTS, product_imports)
        self.assertEqual([], violations)
        self.assertFalse(any(name in source for name in CONCRETE_NAMES), "case source names a concrete provider")

    def test_protocol_registry_and_group_inventory_are_complete(self) -> None:
        """Bind the required lifecycle surface and exact A-J inventory."""

        self.assertTrue(all(isinstance(harness, ProviderHarness) for harness in (JsonHarness(), MySQLHarness(), PostgresHarness())))
        self.assertEqual(("create", "destroy", "reset_fast"), tuple(sorted(name for name in ("create", "destroy", "reset_fast") if hasattr(ProviderHarness, name))))
        self.assertEqual(tuple("ABCDEFGHIJ"), tuple(group.identifier for group in GROUPS))
        registrations = registered_harnesses()
        self.assertEqual(("json", "mysql", "postgres"), tuple(registration.name for registration in registrations))
        self.assertEqual(len(registrations), len({registration.name for registration in registrations}))
        self.assertEqual(tuple(sorted(registration.name for registration in registrations)), tuple(registration.name for registration in registrations))

    def test_reset_group_compares_complete_provider_normalized_fresh_state(self) -> None:
        """Bind group I to complete fresh-state equivalence without provider-specific metadata."""

        case_source = (PACKAGE_ROOT / "cases.py").read_text(encoding="utf-8")
        case_tree = ast.parse(case_source, filename="cases.py")
        group_i = next(node for node in case_tree.body if isinstance(node, ast.FunctionDef) and node.name == "group_i_reset")
        group_source = ast.get_source_segment(case_source, group_i) or ""
        self.assertIn("fresh_players = provider.load_players(_empty_players)", group_source)
        self.assertIn("provider.load_players(_empty_players) == fresh_players", group_source)
        self.assertNotIn('["players"] == []', group_source)


if __name__ == "__main__":
    unittest.main()
