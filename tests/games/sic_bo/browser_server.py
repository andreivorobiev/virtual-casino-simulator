# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Real-shell browser harness for the intentionally unregistered issue #88 slice."""

# Import argument parsing for explicit loopback listener controls.
import argparse
# Import JSON for the inert module proposal and ready-file metadata.
import json
# Import process identity and isolated local-test environment configuration.
import os
# Import temporary-directory ownership so no workspace data is touched.
import tempfile
# Import one watcher thread for graceful listener shutdown by control file.
import threading
# Import bounded polling delay for the game-local shutdown watcher.
import time
# Import interpreter path controls for direct script invocation from this test folder.
import sys
# Import the standard threaded HTTP server used by the production app.
from http.server import ThreadingHTTPServer
# Import path handling for repository and test-control files.
from pathlib import Path

# Reserve both user-owned live-session ports against explicit harness selection.
PROTECTED_LIVE_PORTS = {8765, 8877}


# Read the exact inert descriptor proposed to #77 without duplicating shared metadata.
def load_proposed_module(repository_root: Path) -> dict:
    # Read the game-owned integration handoff as UTF-8 documentation.
    text = (repository_root / "casino" / "games" / "sic_bo" / "INTEGRATION.md").read_text(encoding="utf-8")
    # Extract only the first fenced JSON descriptor from the handoff.
    descriptor_text = text.split("```json", 1)[1].split("```", 1)[0]
    # Parse the exact proposal so browser evidence matches #77's pending input.
    return json.loads(descriptor_text)


# Patch only this process's runtime paths and catalog before importing the application.
def configure_isolated_runtime(repository_root: Path, runtime_root: Path) -> None:
    # Keep the harness on the local JSON provider regardless of developer shell settings.
    os.environ["CASINO_STORAGE_PROVIDER"] = "json"
    # Declare the loopback harness as an explicit test-mode process.
    os.environ["CASINO_DEPLOYMENT_MODE"] = "test"
    # Import configuration before any state, logger, auth, registry, or app module.
    from casino import config, module_versions

    # Redirect every data document into the harness-owned temporary directory.
    config.DATA_DIR = runtime_root / "data"
    # Redirect every player-owned game document beneath the isolated data root.
    config.GAME_DATA_DIR = config.DATA_DIR / "games"
    # Redirect runtime logs away from the repository and live session.
    config.LOG_DIR = runtime_root / "logs"
    # Parse the exact game-local proposal used for the #77 handoff.
    proposed_module = load_proposed_module(repository_root)
    # Copy the proposed game entry before adding validator-owned metadata.
    game_entry = dict(proposed_module["game"])
    # Carry the proposed contract ownership exactly like config.load_game_catalog.
    game_entry["contracts"] = list(proposed_module.get("contracts", []))
    # Carry the proposed source paths exactly like config.load_game_catalog.
    game_entry["paths"] = list(proposed_module.get("paths", []))
    # Add Sic Bo to this process only; no shared descriptor or manifest is changed.
    config.GAMES.append(game_entry)
    # Preserve the canonical sort-order behavior of the production catalog loader.
    config.GAMES.sort(key=lambda game: (int(game.get("sort_order", 9999)), game["id"]))
    # Add the proposed revision to this process only for catalog response rendering.
    module_versions.MODULE_REVISIONS[proposed_module["module"]] = proposed_module["version"]


# Watch one explicit temporary control file and stop the listener gracefully.
def watch_for_stop(server: ThreadingHTTPServer, stop_file: Path) -> None:
    # Poll until the owning worker requests shutdown through its unique control file.
    while not stop_file.exists():
        # Bound polling overhead without blocking the main HTTP server thread.
        time.sleep(0.1)
    # Ask serve_forever to exit through its documented thread-safe path.
    server.shutdown()


# Start one isolated real-app listener and publish exact PID/port evidence.
def main(argv=None) -> int:
    # Create the explicit command-line contract for worker-owned browser evidence.
    parser = argparse.ArgumentParser(description="Run the isolated Sic Bo browser harness")
    # Accept loopback only so the harness cannot become externally reachable.
    parser.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1"])
    # Use operating-system ephemeral allocation unless a safe unprotected port is supplied.
    parser.add_argument("--port", type=int, default=0)
    # Require a unique ready file outside the repository for PID and port discovery.
    parser.add_argument("--ready-file", type=Path, required=True)
    # Require a unique stop file outside the repository for graceful cleanup.
    parser.add_argument("--stop-file", type=Path, required=True)
    # Parse the bounded harness inputs.
    args = parser.parse_args(argv)
    # Reject either protected live-session port even if explicitly requested.
    if args.port in PROTECTED_LIVE_PORTS:
        # Stop before importing or mutating any runtime state.
        raise ValueError("The Sic Bo browser harness cannot use protected live-session ports 8765 or 8877")
    # Resolve the repository root from this game-specific test path.
    repository_root = Path(__file__).resolve().parents[3]
    # Make the repository package importable when Python starts from this script directory.
    sys.path.insert(0, str(repository_root))
    # Own all generated data and logs beneath an automatically cleaned system-temp root.
    with tempfile.TemporaryDirectory(prefix="sic-bo-issue-88-") as temporary_directory:
        # Convert the temporary directory into a stable path object for configuration.
        runtime_root = Path(temporary_directory)
        # Patch isolated paths and the pending descriptor before application import.
        configure_isolated_runtime(repository_root, runtime_root)
        # Import the real application only after all copied config constants are safe.
        from casino import app

        # Create isolated directories before bootstrapping the real storage provider.
        app.ensure_dirs()
        # Run legacy migration only against the empty harness-owned temporary root.
        app.migrate_from_v7_if_needed()
        # Bootstrap default players through the real JSON provider in temporary storage.
        app.bootstrap_players(app.players.default_players)
        # Bootstrap the local test administrator inside the same temporary storage.
        app.auth.bootstrap_admin_from_env()
        # Bind the real application handler to loopback and an ephemeral non-live port.
        server = ThreadingHTTPServer((args.host, args.port), app.Handler)
        # Read the operating-system-selected port after successful binding.
        actual_port = int(server.server_address[1])
        # Build exact process evidence without including credentials or session data.
        ready = {"pid": os.getpid(), "host": args.host, "port": actual_port, "data_root": str(configured_data_root(runtime_root))}
        # Ensure the external control directory exists before publishing readiness.
        args.ready_file.parent.mkdir(parents=True, exist_ok=True)
        # Publish readiness atomically enough for one worker polling a unique filename.
        args.ready_file.write_text(json.dumps(ready, sort_keys=True), encoding="utf-8")
        # Print the same non-secret metadata for the captured validation log.
        print(json.dumps({"sic_bo_browser_server": ready}, sort_keys=True), flush=True)
        # Start one daemon watcher that requests graceful shutdown through serve_forever.
        watcher = threading.Thread(target=watch_for_stop, args=(server, args.stop_file), daemon=True)
        # Begin watching only after the ready metadata is durable.
        watcher.start()
        # Serve the real shell, static assets, auth, catalog, and game endpoints.
        try:
            # Process browser requests until the unique stop control file appears.
            server.serve_forever()
        # Close listener and test controls even if a browser assertion fails upstream.
        finally:
            # Release the loopback socket before reporting command completion.
            server.server_close()
            # Remove only this harness's unique ready file.
            args.ready_file.unlink(missing_ok=True)
            # Remove only this harness's unique stop file.
            args.stop_file.unlink(missing_ok=True)
    # Return success after the temporary data root has also been removed.
    return 0


# Return the configured data path for explicit no-live-data evidence.
def configured_data_root(runtime_root: Path) -> Path:
    # Keep this helper independent of imported shared state modules.
    return runtime_root / "data"


# Run the harness only when invoked as the game-specific test entrypoint.
if __name__ == "__main__":
    # Exit through the normal integer status contract.
    raise SystemExit(main())
