"""Inert descriptor-driven discovery for independently owned game test suites."""

# Import immutable data records for the discovered case packet.
from dataclasses import dataclass
# Import dotted modules declared by a game descriptor.
import importlib
# Import an in-memory stream so focused suite output stays attached to failures.
import io
# Import regular expressions for conservative dotted-module validation.
import re
# Import unittest's existing discovery and execution primitives.
import unittest
# Import mapping and sequence protocols for descriptor validation.
from collections.abc import Mapping, Sequence
# Import Any for the JSON-shaped descriptor boundary.
from typing import Any


# Accept Python dotted module references without executing arbitrary expressions.
_DOTTED_MODULE_RE = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$")


# Represent one invalid or unloadable descriptor-owned test declaration.
class SuiteDiscoveryError(ValueError):
    """Fail closed when descriptor-owned suite evidence is incomplete or invalid."""


# Preserve the immutable metadata needed by a future shared runner integration.
@dataclass(frozen=True)
class GameSuiteCase:  # Keep discovery packets immutable between validation and execution.
    """One descriptor-owned API case whose suites can be loaded on demand."""

    # Retain the canonical catalog game identifier for diagnostics.
    game_id: str
    # Retain the permanent runner case identifier supplied by the descriptor.
    case_id: str
    # Retain requirement mappings in descriptor order.
    requirements: tuple[str, ...]
    # Retain dotted suite modules in descriptor order.
    suite_modules: tuple[str, ...]
    # Retain the discovery-time test count for deterministic execution proof.
    test_count: int

    # Execute fresh suite instances and raise when any declared evidence fails.
    def run(self) -> None:
        # Reload fresh test instances so a discovered packet remains safely reusable.
        suite, current_count = _load_suite_modules(self.game_id, self.suite_modules)
        # Fail closed if import-time registration changed after discovery.
        if current_count != self.test_count:
            # Explain the unstable evidence count without silently running a different suite.
            raise SuiteDiscoveryError(
                f"{self.game_id}: suite test count changed from "  # Name the affected game.
                f"{self.test_count} to {current_count}"  # Report both observed counts.
            )
        # Capture unittest output so a later shared runner receives compact failure evidence.
        output = io.StringIO()
        # Run the complete descriptor-ordered suite through unittest's standard runner.
        result = unittest.TextTestRunner(stream=output, verbosity=1).run(suite)
        # Reject any assertion failure, import sentinel, or execution error.
        if not result.wasSuccessful():
            # Normalize captured output only for the raised diagnostic.
            details = output.getvalue().strip()
            # Raise one stable boundary error for future run_case integration.
            raise AssertionError(
                f"{self.case_id}: descriptor-owned suites failed"  # Identify the runner case.
                f"{': ' + details if details else ''}"  # Append captured unittest evidence.
            )


# Validate one required non-empty descriptor string.
def _required_string(value: Any, field_name: str, game_id: str) -> str:
    # Require a string whose surrounding whitespace is already normalized.
    if not isinstance(value, str) or not value or value != value.strip():
        # Name the exact descriptor field that cannot be trusted.
        raise SuiteDiscoveryError(f"{game_id}: {field_name} must be a non-empty string")
    # Return the validated string without rewriting descriptor content.
    return value


# Validate one ordered non-empty list of unique descriptor strings.
def _required_string_list(value: Any, field_name: str, game_id: str) -> tuple[str, ...]:
    # Reject strings and mappings even though both satisfy broad sequence-like operations.
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        # Require explicit JSON-array semantics at the catalog boundary.
        raise SuiteDiscoveryError(f"{game_id}: {field_name} must be a non-empty list")
    # Validate every item while preserving the descriptor's deterministic order.
    items = tuple(
        _required_string(item, f"{field_name}[{index}]", game_id)  # Validate one entry.
        for index, item in enumerate(value)  # Preserve the declared array order.
    )
    # Reject an explicitly declared but empty evidence list.
    if not items:
        # Distinguish invalid migration metadata from a descriptor with no suites key.
        raise SuiteDiscoveryError(f"{game_id}: {field_name} must be a non-empty list")
    # Reject duplicate evidence that would execute or map the same declaration twice.
    if len(set(items)) != len(items):
        # Require each descriptor-owned entry to be independently meaningful.
        raise SuiteDiscoveryError(f"{game_id}: {field_name} must not contain duplicates")
    # Return one immutable ordered representation.
    return items


# Import and load every declared module through unittest's default loader.
def _load_suite_modules(
    game_id: str, suite_modules: tuple[str, ...]  # Accept the validated discovery inputs.
) -> tuple[unittest.TestSuite, int]:  # Return the composed suite and exact case count.
    # Collect module suites in descriptor order for deterministic execution.
    loaded_suites: list[unittest.TestSuite] = []
    # Count every discovered test for zero-evidence and stability checks.
    total_tests = 0
    # Resolve each independently owned module without a central game allowlist.
    for module_reference in suite_modules:
        # Fail before import when the descriptor contains a non-module expression.
        if _DOTTED_MODULE_RE.fullmatch(module_reference) is None:
            # Explain the exact invalid reference without attempting execution.
            raise SuiteDiscoveryError(
                f"{game_id}: invalid dotted suite module {module_reference!r}"  # Name it.
            )
        # Import only the validated dotted module path.
        try:
            # Use Python's standard import boundary for descriptor-owned modules.
            module = importlib.import_module(module_reference)
        # Convert any import-time failure into the stable discovery boundary.
        except Exception as exc:
            # Preserve the original exception as the diagnostic cause.
            raise SuiteDiscoveryError(
                f"{game_id}: could not import suite module {module_reference!r}"  # Name it.
            ) from exc  # Retain the import failure for debugging without hiding the boundary.
        # Snapshot singleton-loader diagnostics before this module is inspected.
        loader_error_count = len(unittest.defaultTestLoader.errors)
        # Load all TestCase classes and load_tests hooks from the declared module.
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        # Read only loader diagnostics added by this specific declaration.
        loader_errors = unittest.defaultTestLoader.errors[loader_error_count:]
        # Reject loader-created failure sentinels during discovery.
        if loader_errors:
            # Preserve compact loader evidence in the stable discovery error.
            raise SuiteDiscoveryError(
                f"{game_id}: suite module {module_reference!r} could not be loaded: "  # Context.
                f"{loader_errors[-1]}"  # Include the loader's final diagnostic.
            )
        # Count the module's concrete tests before adding it to the aggregate.
        module_test_count = suite.countTestCases()
        # Reject a descriptor that cites a module but proves no behavior.
        if module_test_count == 0:
            # Identify the empty module so the owner can repair its evidence.
            raise SuiteDiscoveryError(
                f"{game_id}: suite module {module_reference!r} contains no tests"  # Name it.
            )
        # Retain the loaded module suite in descriptor order.
        loaded_suites.append(suite)
        # Accumulate the exact discovery-time test count.
        total_tests += module_test_count
    # Compose the ordered module suites into one standard unittest suite.
    return unittest.TestSuite(loaded_suites), total_tests


# Discover one optional descriptor-owned suite case without wiring any shared runner.
def discover_game_suite_case(descriptor: Mapping[str, Any]) -> GameSuiteCase | None:
    """Return a validated suite case, or None for an unmigrated descriptor."""

    # Require the catalog descriptor's game object before reading owned metadata.
    game = descriptor.get("game")
    # Reject malformed catalog input instead of treating it as an unmigrated game.
    if not isinstance(game, Mapping):
        # Keep the failure at the descriptor boundary.
        raise SuiteDiscoveryError("descriptor.game must be an object")
    # Validate the canonical game id used by every diagnostic and future runner row.
    game_id = _required_string(game.get("id"), "game.id", "descriptor")
    # Read the existing module-owned tests object without requiring migration fields.
    tests_spec = game.get("tests")
    # Preserve incremental migration when no tests object is present.
    if tests_spec is None:
        # Return no shared-runner case until the descriptor opts in.
        return None
    # Reject malformed tests metadata even when it has not opted into suites.
    if not isinstance(tests_spec, Mapping):
        # Prevent ambiguous truthy or list-shaped catalog metadata.
        raise SuiteDiscoveryError(f"{game_id}: game.tests must be an object")
    # Preserve incremental migration when the suites key is absent.
    if "suites" not in tests_spec:
        # Leave existing long_driver-only descriptors behaviorally unchanged.
        return None
    # Validate the explicitly declared ordered suite module list.
    suite_modules = _required_string_list(
        tests_spec.get("suites"), "game.tests.suites", game_id  # Validate suite ownership.
    )
    # Validate the permanent case id required by future run_case integration.
    case_id = _required_string(
        tests_spec.get("case_id"), "game.tests.case_id", game_id  # Validate runner identity.
    )
    # Validate every requirement mapping without allocating or rewriting an id.
    requirements = _required_string_list(
        tests_spec.get("requirements"), "game.tests.requirements", game_id  # Validate mappings.
    )
    # Import and count every declared suite now so invalid evidence fails discovery.
    _suite, test_count = _load_suite_modules(game_id, suite_modules)
    # Return immutable metadata with an on-demand runner and no shared-file wiring.
    return GameSuiteCase(
        game_id=game_id,  # Retain the canonical catalog identity.
        case_id=case_id,  # Retain the future shared-runner identity.
        requirements=requirements,  # Retain permanent requirement mappings.
        suite_modules=suite_modules,  # Retain descriptor-owned module ordering.
        test_count=test_count,  # Retain the discovery-time stability guard.
    )
