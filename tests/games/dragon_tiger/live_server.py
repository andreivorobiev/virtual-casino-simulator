# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Launch the real casino app with isolated Dragon Tiger browser-test storage.

This issue-local harness never reads or writes the repository's shared ``data/``
directory. It applies the proposed Dragon Tiger module revision in memory only so
the catalog can exercise the unintegrated descriptor without editing #77-owned
version files.
"""

# Import command-line parsing for explicit temporary-data and readiness paths.
import argparse
# Import JSON support for the machine-readable listener handoff file.
import json
# Import process identifiers for listener cleanup evidence.
import os
# Import the standard threaded loopback server used by the production app.
from http.server import ThreadingHTTPServer
# Import portable filesystem paths for isolated runtime directories.
from pathlib import Path
# Import the operating-system temporary root for fail-closed path validation.
import tempfile
# Import path configuration so direct script execution loads this checkout.
import sys

# Resolve the repository root before importing production packages.
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
# Prefer this exact clean worktree over unrelated installed packages.
sys.path.insert(0, str(REPOSITORY_ROOT))

# Import configuration before the app so test-only path overrides take effect.
import casino.config as config
# Import the canonical revision mapping for one process-local proposal shim.
import casino.module_versions as module_versions

# Bind only to loopback so focused browser validation is never network-exposed.
HOST = "127.0.0.1"
# Protect the user's live Casino listener from accidental reuse.
PROTECTED_PORT = 8765
# Resolve the only parent directory accepted for disposable harness artifacts.
TEMPORARY_ROOT = Path(tempfile.gettempdir()).resolve()


# Parse the explicit isolated-runtime inputs supplied by the validation command.
def parse_args(argv=None):
    # Create a focused parser without inheriting production server defaults.
    parser = argparse.ArgumentParser(description="Run the isolated Dragon Tiger browser harness")
    # Require a temporary data root outside the repository's shared live data.
    parser.add_argument("--data-dir", required=True)
    # Require a readiness file so the caller can record the actual ephemeral port.
    parser.add_argument("--ready-file", required=True)
    # Default to an operating-system-selected ephemeral listener.
    parser.add_argument("--port", type=int, default=0)
    # Return validated command-line arguments to the launcher.
    return parser.parse_args(argv)


# Redirect every mutable runtime path before importing storage, logging, or app code.
def configure_isolated_paths(data_dir: Path) -> None:
    # Point player, auth, ledger, and document storage at the temporary root.
    config.DATA_DIR = data_dir
    # Keep player-owned game documents under the same isolated root.
    config.GAME_DATA_DIR = data_dir / "games"
    # Keep access and validation logs outside the repository and shared session.
    config.LOG_DIR = data_dir / "logs"


# Reject any mutable harness path outside the operating-system temporary root.
def require_temporary_path(path: Path, label: str) -> None:
    # Resolve aliases and parent traversal before comparing ownership boundaries.
    resolved = path.resolve()
    # Reject repository-local paths including the user's protected shared data directory.
    if resolved.is_relative_to(REPOSITORY_ROOT):
        # Fail before directory creation, migration, bootstrap, or listener startup.
        raise ValueError(f"Dragon Tiger harness {label} must stay outside the repository")
    # Reject arbitrary external paths so a typo cannot overwrite another user-owned location.
    if not resolved.is_relative_to(TEMPORARY_ROOT):
        # Require a disposable operating-system temporary location.
        raise ValueError(f"Dragon Tiger harness {label} must stay under {TEMPORARY_ROOT}")


# Start one real registered app instance for issue-scoped browser validation.
def main(argv=None) -> int:
    # Parse all filesystem and listener inputs before runtime mutation.
    args = parse_args(argv)
    # Resolve the caller-owned temporary data path without touching shared data.
    data_dir = Path(args.data_dir).resolve()
    # Resolve the machine-readable listener handoff path.
    ready_file = Path(args.ready_file).resolve()
    # Reject repository/shared data before applying any runtime path override.
    require_temporary_path(data_dir, "data directory")
    # Reject a readiness target that could overwrite a repository or user file.
    require_temporary_path(ready_file, "readiness file")
    # Refuse the live port before opening or probing a socket.
    if args.port == PROTECTED_PORT:
        # Stop before interacting with the user's live Casino listener.
        raise ValueError("Dragon Tiger harness refuses protected port 8765")
    # Apply temporary paths before importing modules that capture configuration.
    configure_isolated_paths(data_dir)
    # Add only the proposed revision in memory so catalog listing can exercise the slice.
    module_versions.MODULE_REVISIONS["dragon_tiger"] = "1.0.0"

    # Import the production handler only after isolated configuration is complete.
    from casino.app import Handler
    # Import auth and player bootstrap services used by production startup.
    from casino.core import auth, players
    # Import production directory and legacy-migration setup under the isolated paths.
    from casino.core.state_store import ensure_dirs, migrate_from_v7_if_needed
    # Import provider-aware player bootstrap under the isolated paths.
    from casino.core.storage import bootstrap_players

    # Apply the same loopback startup safety check as the production server.
    config.validate_bootstrap_for_startup(HOST)
    # Create only temporary data, game-state, and log directories.
    ensure_dirs()
    # Run compatibility migration only against the empty temporary root.
    migrate_from_v7_if_needed()
    # Seed disposable player records through the real storage provider.
    bootstrap_players(players.default_players)
    # Seed the disposable local Admin used by authenticated browser validation.
    auth.bootstrap_admin_from_env()

    # Bind the production request handler to the requested loopback port.
    server = ThreadingHTTPServer((HOST, args.port), Handler)
    # Read the actual operating-system-selected port for the caller handoff.
    bound_port = int(server.server_address[1])
    # Fail closed if an unexpected ephemeral selection reaches the protected port.
    if bound_port == PROTECTED_PORT:
        # Close only the new harness socket before reporting the protected-port error.
        server.server_close()
        # Stop without ever contacting the user's live listener.
        raise RuntimeError("Dragon Tiger harness refused protected port 8765")

    # Create the caller-owned readiness directory when needed.
    ready_file.parent.mkdir(parents=True, exist_ok=True)
    # Build the exact process, port, and data-root cleanup record.
    ready_payload = {"host": HOST, "port": bound_port, "pid": os.getpid(), "data_dir": str(data_dir)}
    # Publish readiness atomically enough for one local launcher/reader pair.
    ready_file.write_text(json.dumps(ready_payload, sort_keys=True), encoding="utf-8")
    # Emit a concise human-readable listener record for captured validation logs.
    print(f"Dragon Tiger browser harness PID {os.getpid()} at http://{HOST}:{bound_port}/", flush=True)

    # Serve authenticated real-app requests until the caller completes validation.
    try:
        # Reuse the production handler's request lifecycle and static file serving.
        server.serve_forever()
    # Close the harness socket when the owning validation process stops normally.
    finally:
        # Release only this ephemeral listener.
        server.server_close()
    # Return success for direct invocation paths that stop gracefully.
    return 0


# Run the focused harness only when invoked as a script.
if __name__ == "__main__":
    # Exit through the launcher result so command failures remain observable.
    raise SystemExit(main())
