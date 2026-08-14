# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Scan or explicitly normalize provider wallet balances to exact cents."""

# Import argument parsing for the explicit check/apply operator modes.
import argparse
# Import JSON encoding for deterministic machine-readable evidence.
import json
# Import portable paths so direct script execution can locate the repository package.
import pathlib
# Import the active module search path for one deterministic repository-root bootstrap.
import sys

# Resolve the repository root independently of the operator's working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Make the checked-out application package importable during direct script execution.
if str(ROOT) not in sys.path:
    # Prepend the trusted checkout so an unrelated installed package cannot shadow it.
    sys.path.insert(0, str(ROOT))

# Import the configured provider boundary without selecting storage in this module.
from casino.core.storage import get_storage_provider


# Parse the explicit operator mode from command-line arguments. (TOOL-019)
def parse_args(argv=None):
    # Create the bounded two-mode command parser.
    parser = argparse.ArgumentParser(description="Scan or normalize durable wallet balances to exact cents")
    # Require callers to distinguish read-only evidence from the one-time write pass.
    parser.add_argument("mode", choices=("check", "apply"), help="read-only residue scan or explicit audited normalization")
    # Return the validated command arguments.
    return parser.parse_args(argv)


# Run one provider-owned scan or explicit normalization pass. (STORAGE-015, LEDGER-036)
def main(argv=None) -> int:
    # Parse the exact requested mode before constructing the configured provider.
    args = parse_args(argv)
    # Resolve the one provider selected by the deployment or local environment.
    provider = get_storage_provider()
    # Execute the provider-owned pass with writes enabled only for the explicit apply mode.
    report = provider.normalize_wallet_balances(apply=args.mode == "apply")
    # Re-scan after an apply so successful output proves zero remaining residue.
    verification = provider.normalize_wallet_balances(apply=False) if args.mode == "apply" else report
    # Add the provider-neutral postcondition without exposing wallet identities or values.
    evidence = {**report, "mode": args.mode, "remaining_residue_count": verification["residue_count"]}
    # Emit one sorted compact object for tickets, CI, and operator receipts.
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    # Fail a read-only check while residue still requires the explicit apply operation.
    if args.mode == "check" and report["residue_count"]:
        # Return one conventional validation failure without mutating storage.
        return 1
    # Fail closed if an apply did not produce an exact-cent rescan.
    if verification["residue_count"]:
        # Return a distinct operator-recovery status after an incomplete write pass.
        return 2
    # Report successful clean scan or verified normalization.
    return 0


# Execute the command only when invoked as a script.
if __name__ == "__main__":
    # Propagate the bounded status code to the calling shell.
    raise SystemExit(main())
