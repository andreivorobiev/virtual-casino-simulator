"""Real-app browser-test launcher with an in-memory isolated-module revision shim."""

# Import argument parsing for explicit loopback port and temporary data paths.
import argparse
# Import paths so the harness can redirect all runtime writes outside the worktree.
from pathlib import Path
# Import the interpreter path list so direct script execution can resolve the repository package.
import sys
# Import a lock so exactly one real roll receives the test-only response hold.
import threading
# Import a monotonic clock and short polling delay for the cross-process release signal.
import time

# Resolve the repository root from the game-owned launcher location.
ROOT = Path(__file__).resolve().parents[3]
# Put the repository package ahead of environment-installed names for this exact source checkout.
if str(ROOT) not in sys.path:
    # Insert the source root without changing any global Python configuration.
    sys.path.insert(0, str(ROOT))


# Start the real application without changing the shared aggregate manifest in this worker lane.
def main(argv=None):
    # Define the narrow command-line interface used only by the focused browser check.
    parser = argparse.ArgumentParser()
    # Require a caller-selected nonshared listener port.
    parser.add_argument("--port", required=True, type=int)
    # Require a temporary runtime root so repository data remains untouched.
    parser.add_argument("--runtime-root", required=True)
    # Parse the explicit harness arguments.
    args = parser.parse_args(argv)
    # Reject either user-owned Casino listener even if a caller supplies one accidentally.
    if args.port in {8765, 8877}:
        # Fail before importing application services or creating runtime state.
        raise ValueError("Focused Chuck-a-Luck browser checks must not use ports 8765 or 8877")
    # Resolve the disposable runtime directory chosen by the parent test process.
    runtime_root = Path(args.runtime_root).resolve()
    # Resolve the temporary signal file that releases only the first committed roll response.
    release_file = runtime_root / "release-first-roll"
    # Import configuration before state modules snapshot its path constants.
    from casino import config as casino_config
    # Import the canonical revision mapping so the test can simulate only #77's pending entry.
    from casino import module_versions
    # Redirect all JSON provider writes into the disposable browser-test directory.
    casino_config.DATA_DIR = runtime_root / "data"
    # Redirect game state into the same disposable runtime tree.
    casino_config.GAME_DATA_DIR = casino_config.DATA_DIR / "games"
    # Redirect application and test logs away from the repository.
    casino_config.LOG_DIR = runtime_root / "logs"
    # Resolve the issue-owned descriptor proposal without restoring runtime auto-discovery.
    proposal_dir = ROOT / "codex" / "tasks" / "artifacts" / "issue-89-chuck-a-luck"
    # Parse the proposal through the production catalog loader so the focused harness exercises its accepted shape.
    proposed_games = casino_config.load_game_catalog(proposal_dir)
    # Add only the isolated proposal to this disposable process after canonical startup discovery has completed.
    casino_config.GAMES.extend(proposed_games)
    # Preserve production catalog ordering inside the focused process after adding the proposal entry.
    casino_config.GAMES.sort(key=lambda game: (int(game.get("sort_order", 9999)), game["id"]))
    # Add only the proposed game revision in memory so catalog responses can render the isolated descriptor.
    module_versions.MODULE_REVISIONS["chuck_a_luck"] = "1.0.0"
    # Import the isolated service before app construction so the focused process can hold one response after commit.
    from casino.games.chuck_a_luck.service import ChuckALuckService
    # Preserve the production roll implementation for the test-only response wrapper.
    production_roll = ChuckALuckService.roll
    # Track whether the dedicated browser process still owes its one controlled response hold.
    hold_state = {"pending": True}
    # Serialize the first-call decision if the threaded server receives overlapping requests.
    hold_lock = threading.Lock()

    # Hold only the first fully committed roll until the browser finishes truthful rolling-state assertions.
    def roll_with_response_hold(service, player_id, request):
        # Execute the complete production ledger and state transaction before delaying its HTTP response.
        result = production_roll(service, player_id, request)
        # Default later requests to immediate production response behavior.
        should_hold = False
        # Select the first completed roll exactly once across handler threads.
        with hold_lock:
            # Claim the one pending hold when this is the first completed roll.
            if hold_state["pending"]:
                # Prevent reduced-motion and retry actions from receiving another hold.
                hold_state["pending"] = False
                # Mark this response as the controlled rolling-evidence boundary.
                should_hold = True
        # Wait only for the focused parent when this call owns the single hold.
        if should_hold:
            # Bound the test-only wait so a broken parent cannot retain the handler indefinitely.
            deadline = time.monotonic() + 120
            # Poll the disposable runtime signal without touching repository or shared runtime data.
            while not release_file.exists() and time.monotonic() < deadline:
                # Yield briefly so the browser process can write its release signal promptly.
                time.sleep(0.02)
            # Fail the focused response if its parent never completed rolling-state assertions.
            if not release_file.exists():
                # Surface a test-only failure after the committed result remains recoverable in player state.
                raise RuntimeError("Focused Chuck-a-Luck roll response was not released")
        # Return the unchanged production payload after the optional evidence boundary.
        return result

    # Install the response hold only inside this dedicated subprocess before route services are constructed.
    ChuckALuckService.roll = roll_with_response_hold
    # Import the real server only after every runtime path and revision seam is ready.
    from casino.app import serve
    # Run the authenticated real backend on loopback without opening an external browser window.
    serve("127.0.0.1", args.port, open_browser=False)


# Execute the focused launcher when invoked as a script.
if __name__ == "__main__":
    # Delegate exit behavior to the real server lifecycle.
    main()
