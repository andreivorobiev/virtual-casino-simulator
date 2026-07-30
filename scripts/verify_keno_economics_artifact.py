"""Fail-closed identity and completeness verification for hosted KENO-027 evidence."""

# Import JSON parsing for the deterministic Long artifact.
import json
# Import the expected protected source identity from the hosted environment.
import os
# Import exact rational parsing so proof fields cannot degrade to float-only evidence.
from fractions import Fraction
# Import path handling for the caller-owned artifact identity.
from pathlib import Path
# Import command arguments for one explicit evidence path.
import sys


# Verify one exact Keno economics artifact and exit nonzero on any mismatch.
def verify(path):
    # Require hosted source provenance instead of accepting a local placeholder.
    expected_source = os.environ.get("GITHUB_SHA", "").strip()
    # Reject verification without an exact hosted source identity.
    if not expected_source:
        # Raise a fixed secret-free diagnostic.
        raise AssertionError("GITHUB_SHA is required")
    # Parse the exact caller-owned JSON artifact.
    evidence = json.loads(path.read_text(encoding="utf-8"))
    # Require immutable source, requirement, class count, and entropy restoration identity.
    if (evidence.get("source_commit"), evidence.get("requirement"), evidence.get("outcome_count"), evidence.get("rng_restored_success_and_failure")) != (expected_source, "KENO-027", 230, True):
        # Reject any stale, foreign, incomplete, or unrestored evidence.
        raise AssertionError("Keno evidence identity mismatch")
    # Require the truthful finite enumeration range used by the proof.
    if evidence.get("low_cent_range") != {"minimum": 0.01, "maximum": 0.99, "step": 0.01}:
        # Reject inaccurate method metadata.
        raise AssertionError("Keno low-cent range mismatch")
    # Read the complete per-pick evidence matrix.
    rows = evidence.get("rows")
    # Require exactly one ordered row for every legal pick count.
    if not isinstance(rows, list) or [row.get("picks") for row in rows] != list(range(1, 21)):
        # Reject missing, duplicate, or reordered spot rows.
        raise AssertionError("Keno evidence rows mismatch")
    # Require the row class counts to reconcile to the complete 230 classes.
    if sum(int(row.get("outcome_classes", 0)) for row in rows) != 230:
        # Reject incomplete outcome evidence.
        raise AssertionError("Keno evidence class total mismatch")
    # Name every exact rational proof field that must accompany additive decimals.
    rational_fields = ("ideal_rtp_fraction", "worst_low_cent_rtp_fraction", "large_amount_upper_bound_fraction")
    # Visit each row so all exact values are parseable positive rationals.
    for row in rows:
        # Visit every required exact field.
        for field in rational_fields:
            # Parse the canonical integer or numerator/denominator string.
            value = Fraction(str(row.get(field, "")))
            # Require a positive house-economics proof value.
            if value <= 0:
                # Reject empty, invalid, or nonpositive exact evidence.
                raise AssertionError(f"Keno exact field invalid: {field}")
    # Emit one sanitized terminal identity without economic outcome details.
    print(f"KENO_ECONOMICS_ARTIFACT VERIFIED source={expected_source} rows=20 outcomes=230")


# Execute verification only through the explicit hosted workflow entrypoint.
if __name__ == "__main__":
    # Require exactly one explicit artifact path.
    if len(sys.argv) != 2:
        # Exit with a fixed usage diagnostic.
        raise SystemExit("usage: verify_keno_economics_artifact.py <artifact>")
    # Verify the resolved caller-owned artifact.
    verify(Path(sys.argv[1]))
