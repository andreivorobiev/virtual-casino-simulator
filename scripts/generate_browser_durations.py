#!/usr/bin/env python3
# Regenerate the reviewed Browser duration profile from exact sharded result evidence. (issue #502)
import json
# Inspect finite float measurements without coercing arbitrary-precision integers.
import math
# Extract the current literal Browser inventory without importing the application runner.
import re
# Read the optional evidence-directory argument.
import sys
# Resolve repository-owned inputs and the tracked output portably.
from pathlib import Path

# Resolve the repository root from this script's tracked location.
ROOT=Path(__file__).resolve().parents[1]
# Point at the exact runner source whose literal BR identifiers define valid profile keys.
RUNNER_PATH=ROOT/'tests'/'run_tests.py'
# Point at the tracked profile consumed by duration-balanced packing.
PROFILE_PATH=ROOT/'tests'/'browser_case_durations.json'
# Bound the reviewed profile before parsing it.
PROFILE_MAX_BYTES=64*1024
# Bound one measured Browser case to the existing suite timeout budget.
MAX_DURATION_SECONDS=3600
# Bound one shard result artifact before parsing it.
RESULT_MAX_BYTES=8*1024*1024
# Keep profile failures fixed and free of caller-controlled values.
PROFILE_ERROR='browser duration profile is invalid'
# Keep evidence failures fixed and free of caller-controlled values.
EVIDENCE_ERROR='browser duration evidence is invalid'

# Reject duplicate JSON keys instead of accepting last-value-wins evidence.
def _unique_object(pairs):
    # Build one object only while every decoded key remains unique.
    result={}
    # Inspect each pair without reflecting it in an error.
    for key,value in pairs:
        # Reject a duplicate before it overwrites reviewed evidence.
        if key in result: raise ValueError(EVIDENCE_ERROR)
        # Retain the unique pair for later shape validation.
        result[key]=value
    # Return the uniquely keyed object.
    return result

# Raise one fixed parser error for JSON NaN and Infinity tokens.
def _reject_constant(_token):
    # Refuse the non-standard numeric constant without echoing it.
    raise ValueError(EVIDENCE_ERROR)

# Read the current literal Browser case inventory from source.
def browser_case_ids():
    # Read the tracked runner as UTF-8 source.
    source=RUNNER_PATH.read_text(encoding='utf-8')
    # Extract each literal Browser run_case identifier in source order.
    return re.findall(r"\brun_case\(\s*['\"](BR-[A-Za-z0-9\-]+)['\"]",source)

# Validate one exact integer or finite float duration without unsafe coercion.
def normalized_duration(value, *, allow_zero):
    # Bound arbitrary-precision integers before any float operation.
    if type(value) is int:
        # Apply the evidence-only zero allowance and shared maximum.
        valid=(value>=0 if allow_zero else value>=1) and value<=MAX_DURATION_SECONDS
    # Validate exact floats separately so isfinite never sees a huge integer.
    elif type(value) is float:
        # Require finite bounded evidence before rounding it.
        valid=math.isfinite(value) and (value>=0 if allow_zero else value>=1) and value<=MAX_DURATION_SECONDS
    # Reject booleans, strings, containers, and every other type.
    else:
        # Mark the unsupported type invalid without reflecting its value.
        valid=False
    # Fail closed with the caller-selected fixed diagnostic.
    if not valid: raise ValueError(EVIDENCE_ERROR if allow_zero else PROFILE_ERROR)
    # Preserve a one-second minimum for packing after accepting a fast measured case.
    return max(1,round(value))

# Load and strictly validate the existing tracked profile before merging evidence.
def load_profile(known_cases):
    # Read bounded raw bytes so filesystem and size failures share one diagnostic.
    try: raw=PROFILE_PATH.read_bytes()
    # Normalize every filesystem failure without disclosing its path.
    except OSError: raise ValueError(PROFILE_ERROR) from None
    # Reject empty or oversized tracked input before decoding.
    if not raw or len(raw)>PROFILE_MAX_BYTES: raise ValueError(PROFILE_ERROR)
    # Decode and parse strict JSON with unique keys and finite constants.
    try: profile=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique_object,parse_constant=_reject_constant)
    # Normalize every parser, Unicode, and recursion failure.
    except (UnicodeDecodeError,ValueError,RecursionError): raise ValueError(PROFILE_ERROR) from None
    # Require a bounded object whose keys can only name current cases.
    if not isinstance(profile,dict) or len(profile)>len(known_cases): raise ValueError(PROFILE_ERROR)
    # Normalize every tracked row only after structural validation.
    normalized={}
    # Inspect each row without reflecting hostile content.
    for case_id,value in profile.items():
        # Reject non-string, unknown, or stale keys.
        if not isinstance(case_id,str) or case_id not in known_cases: raise ValueError(PROFILE_ERROR)
        # Retain the validated whole-second weight.
        normalized[case_id]=normalized_duration(value,allow_zero=False)
    # Return the reviewed starting profile.
    return normalized

# Parse one bounded shard artifact and return its measured Browser rows.
def measured_rows(path, known_cases):
    # Read one result artifact without trusting its name or contents.
    try: raw=path.read_bytes()
    # Normalize every read failure to the fixed evidence error.
    except OSError: raise ValueError(EVIDENCE_ERROR) from None
    # Reject empty or oversized evidence before decoding.
    if not raw or len(raw)>RESULT_MAX_BYTES: raise ValueError(EVIDENCE_ERROR)
    # Parse strict UTF-8 JSON without duplicate keys or non-finite constants.
    try: data=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique_object,parse_constant=_reject_constant)
    # Normalize every malformed artifact without leaking content.
    except (UnicodeDecodeError,ValueError,RecursionError): raise ValueError(EVIDENCE_ERROR) from None
    # Require the retained result-list envelope.
    if not isinstance(data,dict) or not isinstance(data.get('results'),list): raise ValueError(EVIDENCE_ERROR)
    # Collect validated Browser measurements without mutating the tracked profile yet.
    rows=[]
    # Inspect every retained result row.
    for row in data['results']:
        # Require an object before reading its fields.
        if not isinstance(row,dict): raise ValueError(EVIDENCE_ERROR)
        # Ignore non-Browser rows only when their identifier is a string.
        test_id=row.get('test_id')
        # Reject a malformed identifier rather than coercing it.
        if not isinstance(test_id,str): raise ValueError(EVIDENCE_ERROR)
        # Preserve other-suite rows without treating them as duration evidence.
        if not test_id.startswith('BR-'): continue
        # Reject unknown Browser identifiers so stale evidence cannot enter the profile.
        if test_id not in known_cases: raise ValueError(EVIDENCE_ERROR)
        # Require and normalize the measured duration for each Browser row.
        rows.append((test_id,normalized_duration(row.get('duration_seconds'),allow_zero=True)))
    # Return the validated measurements atomically.
    return rows

# Merge validated measurements from every exact shard artifact.
def collect(results_dir):
    # Resolve the current literal case set once.
    known_cases=set(browser_case_ids())
    # Reject duplicate source identifiers before profile handling.
    if len(known_cases)!=len(browser_case_ids()): raise ValueError(EVIDENCE_ERROR)
    # Load the existing profile through the same strict bounds used by the runner.
    profile=load_profile(known_cases)
    # Enumerate deterministic shard artifacts without accepting an unbounded file count.
    try: paths=sorted(results_dir.glob('browser_results_shard_*.json'))
    # Normalize filesystem enumeration failures.
    except OSError: raise ValueError(EVIDENCE_ERROR) from None
    # Reject an excessive evidence set while permitting a dry regeneration.
    if len(paths)>64: raise ValueError(EVIDENCE_ERROR)
    # Validate every artifact completely before applying any of its rows.
    batches=[measured_rows(path,known_cases) for path in paths]
    # Count the validated measurements for the operator summary.
    merged=0
    # Apply each validated batch in deterministic filename order.
    for rows in batches:
        # Merge each measured case into the in-memory profile.
        for test_id,duration in rows:
            # Retain the newest deterministic measurement from ordered evidence.
            profile[test_id]=duration
            # Count the accepted row.
            merged+=1
    # Report only trusted counts and the fixed tracked filename.
    print(f'merged {merged} measured durations into {PROFILE_PATH.name} ({len(profile)} cases)')
    # Return the complete merged map.
    return profile

# Rewrite the tracked profile deterministically after complete validation.
def main(argv):
    # Resolve the optional evidence directory without requiring it to exist.
    results_dir=Path(argv[1]) if len(argv)>1 else ROOT/'logs'/'test-runs'
    # Reject extra positional arguments instead of ignoring them.
    if len(argv)>2: raise ValueError(EVIDENCE_ERROR)
    # Validate and merge every input before opening the tracked output.
    profile=collect(results_dir)
    # Persist sorted reviewable JSON with one trailing newline.
    PROFILE_PATH.write_text(json.dumps(dict(sorted(profile.items())),indent=1,sort_keys=True)+'\n',encoding='utf-8')
    # Exit successfully.
    return 0

# Run the deterministic generator only when invoked as a script.
if __name__=='__main__':
    # Convert fixed validation failures into one-line nonzero CLI diagnostics.
    try: raise SystemExit(main(sys.argv))
    # Print only the fixed value-free profile/evidence message.
    except ValueError as exc: print(str(exc),file=sys.stderr); raise SystemExit(1)
