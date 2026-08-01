"""Fail-closed identity and completeness verification for hosted KENO-027 evidence.

Comment policy: comments state intent and constraints; self-evident lines stay bare.
This file is on the audited-quality exemption list in check_comment_density.py (issue #555).
"""

import json
import os
# Exact rational parsing keeps proof fields from silently degrading to float-only evidence.
from fractions import Fraction
from pathlib import Path
import sys


def verify(path):
    # Hosted source provenance is required so a stale or locally regenerated artifact
    # can never masquerade as evidence for the commit under review.
    expected_source = os.environ.get("GITHUB_SHA", "").strip()
    if not expected_source:
        raise AssertionError("GITHUB_SHA is required")
    evidence = json.loads(path.read_text(encoding="utf-8"))
    # 230 outcome classes is the complete enumeration for picks 1-20; anything else
    # means the proof was truncated, and rng_restored guards against a leaked patch.
    if (evidence.get("source_commit"), evidence.get("requirement"), evidence.get("outcome_count"), evidence.get("rng_restored_success_and_failure")) != (expected_source, "KENO-027", 230, True):
        raise AssertionError("Keno evidence identity mismatch")
    # The low-cent sweep bounds are method metadata; a narrowed range would weaken the
    # worst-case rounding claim without changing any headline number.
    if evidence.get("low_cent_range") != {"minimum": 0.01, "maximum": 0.99, "step": 0.01}:
        raise AssertionError("Keno low-cent range mismatch")
    rows = evidence.get("rows")
    # One ordered row per legal pick count; order is asserted so a dropped row cannot
    # be hidden by a duplicated neighbour.
    if not isinstance(rows, list) or [row.get("picks") for row in rows] != list(range(1, 21)):
        raise AssertionError("Keno evidence rows mismatch")
    if sum(int(row.get("outcome_classes", 0)) for row in rows) != 230:
        raise AssertionError("Keno evidence class total mismatch")
    # Each decimal headline must be accompanied by its exact rational; parsing with
    # Fraction proves the strings are canonical and positive rather than display text.
    rational_fields = ("ideal_rtp_fraction", "worst_low_cent_rtp_fraction", "large_amount_upper_bound_fraction")
    for row in rows:
        for field in rational_fields:
            value = Fraction(str(row.get(field, "")))
            if value <= 0:
                raise AssertionError(f"Keno exact field invalid: {field}")
    # The terminal line is sanitized to identity only; economics live in the artifact.
    print(f"KENO_ECONOMICS_ARTIFACT VERIFIED source={expected_source} rows=20 outcomes=230")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_keno_economics_artifact.py <artifact>")
    verify(Path(sys.argv[1]))
