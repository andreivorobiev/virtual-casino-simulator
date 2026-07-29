#!/usr/bin/env python3
# Regenerate the tracked browser per-case duration profile from sharded run evidence. (issue #502)
#
# Usage: python scripts/generate_browser_durations.py [results_dir]
# Reads every browser_results_shard_*.json under results_dir (default logs/test-runs), collects the
# duration_seconds recorded per executed case, and rewrites tests/browser_case_durations.json so the
# duration-balanced shard packer keeps working from fresh measured data.
import json
import sys
from pathlib import Path

# Resolve the repository root from this script's location.
ROOT = Path(__file__).resolve().parents[1]
# Point at the tracked profile consumed by the shard packer.
PROFILE_PATH = ROOT / "tests" / "browser_case_durations.json"


# Merge measured durations from every shard result file into one profile map.
def collect(results_dir: Path) -> dict:
    # Start from the existing tracked profile so unmeasured cases keep their last known weight.
    try:
        # Read the current tracked profile when present.
        profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    # Treat a missing or corrupt profile as empty rather than failing regeneration.
    except (OSError, ValueError):
        # Begin with an empty profile.
        profile = {}
    # Track how many measured rows were merged for the summary line.
    merged = 0
    # Read every shard result file in deterministic order.
    for path in sorted(results_dir.glob("browser_results_shard_*.json")):
        # Parse one shard's retained result evidence.
        data = json.loads(path.read_text(encoding="utf-8"))
        # Merge each executed case's measured duration.
        for row in data.get("results", []):
            # Use only browser rows that carry a measured duration.
            if str(row.get("test_id", "")).startswith("BR-") and isinstance(row.get("duration_seconds"), (int, float)):
                # Store whole seconds with a one-second floor so weights stay positive.
                profile[row["test_id"]] = max(1, round(row["duration_seconds"]))
                # Count the merged measurement.
                merged += 1
    # Report the merge without failing when no new evidence exists.
    print(f"merged {merged} measured durations into {PROFILE_PATH.name} ({len(profile)} cases)")
    # Return the merged profile map.
    return profile


# Rewrite the tracked profile deterministically for reviewable diffs.
def main(argv) -> int:
    # Resolve the evidence directory from the optional argument.
    results_dir = Path(argv[1]) if len(argv) > 1 else ROOT / "logs" / "test-runs"
    # Merge measured evidence over the existing profile.
    profile = collect(results_dir)
    # Persist the profile sorted by case id with a trailing newline.
    PROFILE_PATH.write_text(json.dumps(dict(sorted(profile.items())), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    # Exit successfully.
    return 0


# Run as a CLI when invoked directly.
if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
