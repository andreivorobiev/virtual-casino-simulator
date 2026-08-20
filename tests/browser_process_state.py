# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own disposable Browser data and fresh parent-process fixture writes. (TEST-242)"""

# Import temporary-directory ownership so every Browser invocation gets one private root.
import tempfile
# Resolve the private data and log directories without depending on process cwd.
from pathlib import Path


# Configure Browser-only persistence before any casino module captures runtime directories.
def prepare_browser_data_environment(argv, environment, temporary_directory_factory=tempfile.TemporaryDirectory):
    # Leave API, storage, aggregate-verification, and imported-test processes unchanged.
    if "--browser" not in argv:
        # Return no owner when the current process will not start Browser acceptance.
        return None
    # Allocate one process-owned root that is automatically removed after listener shutdown and interpreter exit.
    owner = temporary_directory_factory(prefix="casino-browser-")
    # Resolve the unique root once so data and diagnostic logs cannot escape into the checkout.
    invocation_root = Path(owner.name)
    # Pin Browser acceptance to the JSON provider whose cross-process behavior is under test.
    environment["CASINO_STORAGE_PROVIDER"] = "json"
    # Give the parent harness and inherited child server one exact isolated persistence root.
    environment["CASINO_DATA_DIR"] = str(invocation_root / "data")
    # Keep server diagnostics beside the disposable data without changing retained test artifacts.
    environment["CASINO_LOG_DIR"] = str(invocation_root / "logs")
    # Retain the owner for the process lifetime so automatic cleanup cannot run while the child server is active.
    return owner


# Execute one parent-process fixture mutation through a cache-free provider over current child-owned bytes.
def run_fresh_json_fixture_write(callback, *, data_dir, provider_factory, install_provider):
    # Construct a new provider so no registry cache from an earlier child-server state can be reused.
    provider = provider_factory(Path(data_dir))
    # Route the existing state_store facade through only this isolated provider for the callback.
    install_provider(provider)
    # Preserve the caller's result or exact fail-closed exception without retrying the mutation.
    try:
        # Execute the fixture write once after the fresh provider validates current durable journal bytes.
        return callback()
    # Clear the process-global test seam even when current durable bytes fail validation.
    finally:
        # Force the next parent fixture boundary to construct another current provider instead of retaining this cache.
        install_provider(None)
