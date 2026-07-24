#!/usr/bin/env python3
"""Run the BAC-026/TEST-099 exact-source 2,000-round Baccarat UI qualification."""

import argparse  # Parse only bounded output, progress, and headed-debug options.
import asyncio  # Execute the shared asynchronous browser qualification controller.
import json  # Read the terminal aggregate before applying the focused acceptance gate.
import tempfile  # Keep disposable server copies outside the source checkout.
from pathlib import Path  # Resolve portable report, shard, evidence, and runtime paths.

from tests import ui_50000  # Reuse the accepted rendered-control and cleanup harness.


# Publish one stable browser-test identity for requirement and PR evidence.
TEST_ID = "BR-BAC-SUSTAINED-001"
# Bind focused evidence to new permanent Baccarat and Tests requirements.
REQUIREMENT_IDS = ("BAC-026", "TEST-099")
# Preserve the issue-owned consecutive-round threshold without caller overrides.
EXPECTED_ROUNDS = 2_000


# Build the immutable focused profile consumed by the shared browser controller.
def build_arguments(output_root, progress_every=250, headed=False):
    root = Path(output_root).expanduser().resolve()  # Resolve one caller-owned evidence directory.
    return argparse.Namespace(  # Return every option required by ui_50000.run_all.
        total_cycles=EXPECTED_ROUNDS,  # Require exactly 2,000 assigned Baccarat rounds.
        parallel=1,  # Use one isolated browser, session, account, and loopback runtime.
        only_games="baccarat",  # Prevent unrelated catalog work from diluting the gate.
        deployment_root=str(Path(tempfile.gettempdir()) / "casino-baccarat-sustained"),  # Keep disposable runtime state outside Git.
        report=str(root / "baccarat_sustained.json"),  # Persist one terminal focused report.
        shard_report_root=str(root / "shards"),  # Preserve the single exact-source shard handback.
        evidence_root=str(root / "visual"),  # Preserve governed viewport screenshots for diagnosis.
        progress_every=int(progress_every),  # Emit bounded sanitized progress during the long run.
        roulette_replicas=1,  # Satisfy the shared allocator without creating irrelevant workers.
        replicate_games="",  # Keep the sequence in one uninterrupted Baccarat session.
        game_replicas=1,  # Prevent a passing aggregate from combining shorter parallel sequences.
        resume_shards=False,  # Refuse evidence from an earlier head or interrupted sequence.
        max_attempts_per_cycle=1,  # Treat the first disappearance or timeout as a terminal failure.
        headed=bool(headed),  # Permit an explicitly visible browser only for focused diagnosis.
        keep_deployments=False,  # Always remove the test-owned runtime after listener closure.
        allocation_index=None,  # Run the focused controller rather than a formal matrix worker.
        aggregate_only=False,  # Launch the real browser instead of accepting downloaded reports.
        source_commit="",  # Let the clean-checkout gate resolve the exact immutable source.
    )


# Count exact visible Deal activations across the focused shard inventory.
def deal_activation_count(report):
    total = 0  # Start with no accepted rendered Deal actions.
    for shard in report.get("shards", []):  # Inspect every shard even though the profile permits one.
        for signature, count in shard.get("control_activated_counts", {}).items():  # Read namespaced public-control counts.
            if "baccarat-deal" in signature:  # Select only the stable Deal test identity.
                total += int(count)  # Accumulate real pointer activations.
    return total  # Return the exact accepted Deal-action count.


# Return bounded acceptance errors for one terminal focused report.
def qualification_errors(report):
    errors = []  # Preserve concise machine-readable gate failures.
    if report.get("status") != "PASS":  # Require the shared harness to accept every universal gate.
        errors.append("shared qualification status is not PASS")  # Keep the focused result fail closed.
    source_commit = str(report.get("source_commit", ""))  # Normalize untrusted report provenance for strict validation.
    if len(source_commit) != 40 or any(character not in "0123456789abcdefABCDEF" for character in source_commit):  # Require one full hexadecimal Git object identity.
        errors.append("source commit is not a full SHA")  # Reject mutable or abbreviated evidence.
    if report.get("requested_cycles") != EXPECTED_ROUNDS:  # Require the issue-owned request volume.
        errors.append("requested cycle count is not 2000")  # Reject shortened rehearsals.
    if report.get("selected_games") != ["baccarat"]:  # Require the single intended module.
        errors.append("selected game inventory is not Baccarat-only")  # Reject mixed-catalog evidence.
    if report.get("worker_count") != 1:  # Require one uninterrupted session rather than merged shards.
        errors.append("worker count is not one")  # Reject parallel fragments.
    if report.get("attempted_cycles") != EXPECTED_ROUNDS or report.get("completed_cycles") != EXPECTED_ROUNDS:  # Require every assigned round to complete.
        errors.append("attempted and completed cycles are not exactly 2000")  # Reject gaps and partial runs.
    if report.get("failed_cycles") != 0 or report.get("failed_attempts") != 0:  # Forbid retries, timeouts, and recovered control replacement.
        errors.append("one or more Baccarat attempts failed")  # Preserve the core issue #265 gate.
    if not report.get("assignment", {}).get("no_gaps_or_duplicates"):  # Require the exact 0-through-1999 identity range.
        errors.append("cycle assignment has a gap or duplicate")  # Reject ambiguous accounting.
    game_counts = report.get("game_counts", {})  # Read the canonical per-game aggregate.
    baccarat = game_counts.get("baccarat", {}) if set(game_counts) == {"baccarat"} else {}  # Accept only one canonical game record.
    if baccarat.get("quota") != EXPECTED_ROUNDS or baccarat.get("completed") != EXPECTED_ROUNDS:  # Require the full game-owned sequence.
        errors.append("Baccarat aggregate does not contain 2000 completed rounds")  # Reject a mixed or incomplete total.
    if baccarat.get("failed") != 0 or baccarat.get("failed_attempts") != 0 or baccarat.get("status") != "PASS":  # Preserve per-game fail-closed state.
        errors.append("Baccarat aggregate contains a failure")  # Reject controller/report disagreement.
    if deal_activation_count(report) != EXPECTED_ROUNDS:  # Require one accepted rendered Deal per completed coup.
        errors.append("visible Baccarat Deal activation count is not 2000")  # Detect a hidden shortcut or missing control action.
    if report.get("failure_counts") or report.get("visual_failures"):  # Reject grouped product and governed-geometry failures.
        errors.append("qualification recorded product or visual failures")  # Preserve diagnostic evidence without accepting it.
    diagnostics = report.get("browser_diagnostics", {})  # Read sanitized console, page, and HTTP counters.
    if any(diagnostics.get(name) for name in ("console_errors", "page_errors", "http_failures")):  # Require a clean browser surface.
        errors.append("qualification recorded browser diagnostics")  # Reject hidden runtime failures.
    if not all(report.get(name) for name in ("shards_pass", "isolation_ok", "listener_cleanup_ok", "visuals_complete")):  # Require universal safety/evidence gates.
        errors.append("one or more shard, isolation, cleanup, or visual gates failed")  # Keep listener and account isolation mandatory.
    return errors  # Return every focused gate failure without leaking local details.


# Stamp the shared aggregate with the focused permanent requirement mapping.
def stamp_report(report):
    errors = qualification_errors(report)  # Evaluate the complete terminal aggregate.
    report["qualification"] = {  # Add one durable focused acceptance record.
        "test_id": TEST_ID,  # Publish the stable browser-test identity.
        "requirements": list(REQUIREMENT_IDS),  # Bind the result to BAC-026 and TEST-099.
        "expected_consecutive_rounds": EXPECTED_ROUNDS,  # Preserve the non-negotiable issue threshold.
        "maximum_attempts_per_round": 1,  # Disclose that no recovery attempt can be accepted.
        "visible_deal_activations": deal_activation_count(report),  # Record the rendered Deal proof.
        "status": "PASS" if not errors else "FAIL",  # Accept only when every focused gate passes.
        "errors": errors,  # Retain bounded actionable failures.
    }
    report["status"] = "PASS" if not errors else "FAIL"  # Keep the top-level result aligned with the focused gate.
    return errors  # Let the command choose its terminal exit status.


# Run the focused profile and persist its final requirement-stamped evidence.
def run_profile(arguments):
    exit_code = asyncio.run(ui_50000.run_all(arguments))  # Execute the real rendered-control qualification.
    report_path = Path(arguments.report).expanduser().resolve()  # Resolve the shared terminal aggregate.
    if not report_path.exists():  # Defend against a controller failure before report persistence.
        print(f"{TEST_ID} FAIL report_missing", flush=True)  # Emit one secret-safe terminal diagnostic.
        return 1  # Fail without fabricating evidence.
    report = json.loads(report_path.read_text(encoding="utf-8"))  # Read the exact-source aggregate.
    errors = stamp_report(report)  # Apply the stricter uninterrupted-sequence gate.
    ui_50000.write_json(report_path, report)  # Persist the permanent requirement mapping beside the evidence.
    status = "PASS" if exit_code == 0 and not errors else "FAIL"  # Require both shared and focused controllers to agree.
    print(f"{TEST_ID} {status} rounds={report.get('completed_cycles', 0)}/{EXPECTED_ROUNDS} failed_attempts={report.get('failed_attempts', 0)}", flush=True)  # Emit sanitized terminal counts.
    return 0 if status == "PASS" else 1  # Return the exact focused acceptance status.


# Parse only the safe operator choices that do not weaken qualification semantics.
def parse_args():
    parser = argparse.ArgumentParser(description="Run exactly 2,000 consecutive Baccarat rounds through rendered browser controls.")  # Create the bounded CLI.
    parser.add_argument("--output-root", default=str(ui_50000.ROOT / "logs" / "test-runs" / "baccarat_sustained"), help="Directory for sanitized report and visual evidence.")  # Configure test-owned output.
    parser.add_argument("--progress-every", type=int, default=250, help="Sanitized progress interval.")  # Permit useful monitoring without changing volume.
    parser.add_argument("--headed", action="store_true", help="Show the focused browser for local diagnosis.")  # Keep CI headless by default.
    options = parser.parse_args()  # Parse caller input once.
    if options.progress_every < 1:  # Reject invalid progress configuration.
        parser.error("--progress-every must be at least 1")  # Preserve bounded monitoring.
    return build_arguments(options.output_root, options.progress_every, options.headed)  # Return the immutable shared-harness namespace.


# Enter only when the focused qualification is launched directly.
if __name__ == "__main__":
    raise SystemExit(run_profile(parse_args()))  # Exit with BR-BAC-SUSTAINED-001 status.
