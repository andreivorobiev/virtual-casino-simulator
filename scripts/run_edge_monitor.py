# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Run the production edge observer with a strictly parsed root-managed bearer."""

# Import command-line parsing for the fixed monitor-file and policy inputs.
import argparse
# Import paths without exposing them in command output.
import pathlib
# Import bounded secret-safe error reporting.
import sys

# Select package imports during tests and sibling imports during direct release execution.
if __package__:
    # Import the observer and strict environment reader through the repository namespace.
    from scripts import edge_gate, validate_monitor_config
else:
    # Import packaged sibling scripts when the extracted release executes this file directly.
    import edge_gate
    # Import the packaged strict environment reader without changing sys.path.
    import validate_monitor_config


# Run one read-only observation with only the validated Authorization assignment.
def run_observation(monitor_path: pathlib.Path, policy_path: pathlib.Path, gate_main=None) -> int:
    # Parse and validate the exact bearer assignment without evaluating shell syntax.
    authorization = validate_monitor_config.validated_authorization(monitor_path)
    # Use the production observer unless a listener-free test supplies a capture seam.
    selected_gate = edge_gate.main if gate_main is None else gate_main
    # Pass one exact in-memory credential to the observer without mutating global process state.
    environment = {edge_gate.AUTHORIZATION_ENV: authorization}
    # Execute the existing read-only observer with the reviewed policy path.
    return selected_gate(["observe", "--policy", str(policy_path)], environ=environment)


# Parse the fixed production inputs and collapse file failures into a secret-safe result.
def main(argv=None) -> int:
    # Describe the non-shell monitor runner without accepting arbitrary commands.
    parser = argparse.ArgumentParser(description="Run the Casino edge monitor without shell-sourcing credentials.")
    # Require the root-managed monitor EnvironmentFile path.
    parser.add_argument("--monitor-env", type=pathlib.Path, required=True, help="Root-managed monitor EnvironmentFile")
    # Require the already packaged restricted-preview policy path.
    parser.add_argument("--policy", type=pathlib.Path, required=True, help="Restricted-preview edge policy")
    # Parse only the two reviewed path inputs.
    args = parser.parse_args(argv)
    # Bound parsing and filesystem failures without printing secret-bearing values.
    try:
        # Run the read-only edge observation through the strict in-process handoff.
        return run_observation(args.monitor_env, args.policy)
    # Convert expected environment-file failures to one fixed category.
    except (OSError, ValueError):
        # Emit no path, assignment, token, digest, or shell text.
        print("edge monitor configuration invalid", file=sys.stderr)
        # Fail closed before any observation when credential loading is invalid.
        return 1


# Execute the direct packaged entrypoint only when invoked as a script.
if __name__ == "__main__":
    # Propagate the observer or fail-closed loader status.
    raise SystemExit(main())
