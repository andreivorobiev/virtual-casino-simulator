# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import JSON support so runtime version metadata can come from the canonical manifest.
import json
# Import Path so the manifest is resolved relative to this source checkout or packaged tree.
from pathlib import Path

# Resolve the repository root without depending on the process working directory.
ROOT_DIR = Path(__file__).resolve().parents[1]
# Point to the single canonical source for packaged and module version metadata.
VERSION_MANIFEST_PATH = ROOT_DIR / "modules" / "module-manifest.json"
# Load the canonical version manifest once during process startup.
VERSION_MANIFEST = json.loads(VERSION_MANIFEST_PATH.read_text(encoding="utf-8"))
# Expose the formal packaged application release used by runtime, API, and Admin surfaces.
APP_VERSION = VERSION_MANIFEST["application"]
# Expose historical source provenance separately from the packaged application release.
SOURCE_BASELINE_VERSION = VERSION_MANIFEST["source_baseline"]
# Copy independent module revisions so callers cannot mutate the loaded manifest object.
MODULE_REVISIONS = dict(VERSION_MANIFEST["modules"])

# Define the list_module_revisions function used by Admin version surfaces.
def list_module_revisions():
    # Return fresh records in canonical manifest order for deterministic API responses.
    return [{"module": module, "revision": revision} for module, revision in MODULE_REVISIONS.items()]
