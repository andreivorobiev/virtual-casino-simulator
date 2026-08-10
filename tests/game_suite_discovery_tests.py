"""Browser-free proof for the inert descriptor-driven game suite loader."""

# Import sys so synthetic dotted modules can be installed without writing fixtures.
import sys
# Import dynamic module objects for isolated descriptor-owned suite fixtures.
import types
# Import unittest for dependency-free focused regression coverage.
import unittest
# Import patch for scoped synthetic module registration.
from unittest.mock import patch

# Import the discovery boundary and its stable failure type.
from tests.game_suite_discovery import (
    GameSuiteCase,  # Assert the immutable discovery packet type.
    SuiteDiscoveryError,  # Assert the stable fail-closed boundary.
    discover_game_suite_case,  # Exercise descriptor-owned discovery.
)


# Build one full module descriptor around optional test metadata.
def descriptor_with(tests_spec):
    # Return the same nested shape used by modules/<game>.json.
    return {"game": {"id": "fixture_game", "tests": tests_spec}}


# Build one importable synthetic unittest module with an optional test outcome.
def synthetic_suite_module(module_name, *, outcome="pass", events=None):
    # Create a module that importlib can resolve from the scoped sys.modules patch.
    module = types.ModuleType(module_name)
    # Retain a shared event list when deterministic module ordering is under test.
    observed_events = events if events is not None else []

    # Define one standard unittest case that belongs to the synthetic module.
    class SyntheticCase(unittest.TestCase):
        # Execute the requested passing or failing fixture behavior.
        def test_fixture_behavior(self):
            # Record the module name before any deliberate assertion failure.
            observed_events.append(module_name)
            # Fail only the explicit failing fixture.
            if outcome == "fail":
                # Produce normal unittest failure evidence for runner propagation.
                self.fail("synthetic suite failure")

    # Make unittest diagnostics identify the synthetic dotted module.
    SyntheticCase.__module__ = module_name
    # Expose the TestCase through the module's public namespace.
    module.SyntheticCase = SyntheticCase
    # Return both the module and its observable execution record.
    return module, observed_events


# Verify optional migration, validation, deterministic loading, and failure propagation.
class GameSuiteDiscoveryTests(unittest.TestCase):
    # Confirm existing long-driver-only descriptors remain behaviorally inert.
    def test_unmigrated_descriptor_returns_no_case(self):
        # Model today's catalog metadata without any suites opt-in.
        descriptor = descriptor_with(
            {"long_driver": "tests.game_drivers.fixture_game:play"}  # Preserve legacy metadata.
        )
        # Verify discovery performs no implicit suite selection.
        self.assertIsNone(discover_game_suite_case(descriptor))

    # Confirm two declared modules load and execute in descriptor order.
    def test_discovers_and_runs_declared_modules_deterministically(self):
        # Retain one shared execution record across both synthetic modules.
        events = []
        # Build the first independently owned suite.
        first_module, _first_events = synthetic_suite_module(
            "tests.synthetic_suite_first", events=events  # Record first-module execution.
        )
        # Build the second independently owned suite.
        second_module, _second_events = synthetic_suite_module(
            "tests.synthetic_suite_second", events=events  # Record second-module execution.
        )
        # Register only the two declared dotted modules for this test.
        with patch.dict(
            sys.modules,  # Isolate imports to the synthetic descriptor-owned modules.
            {
                first_module.__name__: first_module,  # Register the first dotted module.
                second_module.__name__: second_module,  # Register the second dotted module.
            },
        ):  # Keep synthetic registration scoped to this deterministic proof.
            # Discover one immutable case packet from descriptor-owned metadata.
            case = discover_game_suite_case(
                descriptor_with(  # Build the same nested shape as a catalog descriptor.
                    {
                        "case_id": "API-FIXTURE-001",  # Supply the permanent runner identity.
                        "requirements": ["FIXTURE-001", "TEST-042"],  # Map evidence.
                        "suites": [  # Declare independently owned modules in execution order.
                            first_module.__name__,  # Execute the first module first.
                            second_module.__name__,  # Execute the second module second.
                        ],
                    }
                )
            )
            # Require a concrete packet after the descriptor explicitly opts in.
            self.assertIsInstance(case, GameSuiteCase)
            # Verify metadata order is preserved without normalization.
            self.assertEqual(
                (  # Define the exact descriptor-owned metadata expected from discovery.
                    "fixture_game",  # Preserve the canonical game identity.
                    "API-FIXTURE-001",  # Preserve the shared-runner case identity.
                    ("FIXTURE-001", "TEST-042"),  # Preserve requirement ordering.
                    (first_module.__name__, second_module.__name__),  # Preserve suite ordering.
                    2,  # Count one test from each synthetic module.
                ),
                (  # Read the immutable discovery packet without rewriting it.
                    case.game_id,  # Compare the canonical game identity.
                    case.case_id,  # Compare the runner case identity.
                    case.requirements,  # Compare the ordered requirement mappings.
                    case.suite_modules,  # Compare the ordered module references.
                    case.test_count,  # Compare the exact discovered test count.
                ),
            )
            # Execute fresh suite instances through the packet's inert runner.
            case.run()
        # Verify the descriptor order controls execution order.
        self.assertEqual(
            [first_module.__name__, second_module.__name__],  # Define expected ordering.
            events,  # Compare the shared execution record.
        )

    # Confirm explicit suite migration cannot omit required mapping metadata.
    def test_rejects_missing_or_invalid_suite_metadata(self):
        # Build one valid module so metadata validation is the only variable.
        module, _events = synthetic_suite_module("tests.synthetic_suite_metadata")
        # Define invalid opt-in declarations and their stable failure fragments.
        invalid_specs = [
            (  # Reject a suite declaration without a permanent case identity.
                {"requirements": ["FIXTURE-001"], "suites": [module.__name__]},  # Omit it.
                "game.tests.case_id",  # Require the precise missing-field diagnostic.
            ),
            (  # Reject a suite declaration without requirement evidence.
                {
                    "case_id": "API-FIXTURE-001",  # Keep the case identity valid.
                    "requirements": [],  # Deliberately omit permanent mappings.
                    "suites": [module.__name__],  # Keep the module reference valid.
                },
                "game.tests.requirements",  # Require the precise empty-list diagnostic.
            ),
            (  # Reject a suite declaration without executable evidence.
                {
                    "case_id": "API-FIXTURE-001",  # Keep the case identity valid.
                    "requirements": ["FIXTURE-001"],  # Keep requirement evidence valid.
                    "suites": [],  # Deliberately omit suite modules.
                },
                "game.tests.suites",  # Require the precise empty-suite diagnostic.
            ),
            (  # Reject duplicate execution evidence.
                {
                    "case_id": "API-FIXTURE-001",  # Keep the case identity valid.
                    "requirements": ["FIXTURE-001"],  # Keep requirement evidence valid.
                    "suites": [module.__name__, module.__name__],  # Repeat one module.
                },
                "must not contain duplicates",  # Require duplicate-specific rejection.
            ),
            (  # Reject expressions that are not dotted Python modules.
                {
                    "case_id": "API-FIXTURE-001",  # Keep the case identity valid.
                    "requirements": ["FIXTURE-001"],  # Keep requirement evidence valid.
                    "suites": ["not a dotted module"],  # Supply unsafe import syntax.
                },
                "invalid dotted suite module",  # Require syntax-specific rejection.
            ),
        ]
        # Register the valid fixture module for every table-driven declaration.
        with patch.dict(sys.modules, {module.__name__: module}):
            # Exercise every malformed opt-in independently.
            for tests_spec, expected_message in invalid_specs:
                # Name the failing declaration in unittest output.
                with self.subTest(expected_message=expected_message):
                    # Require the descriptor boundary to fail closed.
                    with self.assertRaisesRegex(
                        SuiteDiscoveryError, expected_message  # Match the stable diagnostic.
                    ):  # Scope the rejected declaration to this table row.
                        # Attempt discovery without any shared-runner integration.
                        discover_game_suite_case(descriptor_with(tests_spec))

    # Confirm an import failure does not become an empty or passing case.
    def test_rejects_missing_suite_module(self):
        # Declare a syntactically valid dotted path that is intentionally absent.
        descriptor = descriptor_with(
            {
                "case_id": "API-FIXTURE-001",  # Keep the runner identity valid.
                "requirements": ["FIXTURE-001"],  # Keep requirement evidence valid.
                "suites": ["tests.synthetic_suite_missing"],  # Name the absent module.
            }
        )
        # Require a stable discovery error that identifies the missing module.
        with self.assertRaisesRegex(
            SuiteDiscoveryError, "could not import suite module"  # Match the stable boundary.
        ):  # Scope the missing-module attempt to this assertion.
            # Attempt discovery without installing the declared module.
            discover_game_suite_case(descriptor)

    # Confirm an importable module with no tests cannot count as evidence.
    def test_rejects_zero_test_suite_module(self):
        # Create an importable dotted module with no TestCase declarations.
        module = types.ModuleType("tests.synthetic_suite_empty")
        # Register the empty module only for this focused check.
        with patch.dict(sys.modules, {module.__name__: module}):
            # Require explicit zero-test rejection during discovery.
            with self.assertRaisesRegex(SuiteDiscoveryError, "contains no tests"):
                # Attempt to opt the empty module into the shared evidence packet.
                discover_game_suite_case(
                    descriptor_with(  # Build one otherwise valid descriptor.
                        {
                            "case_id": "API-FIXTURE-001",  # Supply the case identity.
                            "requirements": ["FIXTURE-001"],  # Supply requirement evidence.
                            "suites": [module.__name__],  # Cite the empty module.
                        }
                    )
                )

    # Confirm a discovered suite's assertion failure reaches the future runner boundary.
    def test_runner_propagates_declared_suite_failure(self):
        # Build one importable suite whose only test fails normally.
        module, _events = synthetic_suite_module(
            "tests.synthetic_suite_failing", outcome="fail"  # Request one assertion failure.
        )
        # Register the failing suite for both discovery and on-demand execution.
        with patch.dict(sys.modules, {module.__name__: module}):
            # Discover a valid packet before exercising its runner.
            case = discover_game_suite_case(
                descriptor_with(  # Build one valid explicit suite opt-in.
                    {
                        "case_id": "API-FIXTURE-FAIL-001",  # Identify the failing case.
                        "requirements": ["FIXTURE-001"],  # Retain mapped evidence.
                        "suites": [module.__name__],  # Declare the failing suite.
                    }
                )
            )
            # Require the packet to exist for a valid opt-in declaration.
            self.assertIsNotNone(case)
            # Require normal unittest failure evidence to become a raised boundary error.
            with self.assertRaisesRegex(
                AssertionError, "descriptor-owned suites failed"  # Match stable propagation.
            ):  # Scope the failing run to this assertion.
                # Run a fresh copy of the declared failing suite.
                case.run()


# Run the focused proof directly when invoked outside the repository runner.
if __name__ == "__main__":
    # Delegate process status and reporting to unittest.
    unittest.main()
