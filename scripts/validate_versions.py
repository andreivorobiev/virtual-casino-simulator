# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import JSON support for canonical, module, and compatibility manifests.
import json
# Import pathlib so every validated surface is resolved from the repository root.
import pathlib
# Import regular expressions for semantic and package-version extraction.
import re
# Import sys so the repository package can be loaded during runtime-alignment checks.
import sys

# Resolve the repository root independently of the caller's working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Point to the canonical aggregate version manifest.
MANIFEST = ROOT / "modules" / "module-manifest.json"
# Point to the user-facing repository status document.
README = ROOT / "README.md"
# Point to the Codex starter document that repeats packaged-release context.
STARTER = ROOT / "CODEX_START_HERE.md"
# Point to the generated requirements document that labels both version classes.
GENERATED_REQUIREMENTS = ROOT / "docs" / "requirements" / "requirements_generated.md"
# Point to canonical requirement metadata whose provenance must not masquerade as a release.
REQUIREMENTS = ROOT / "docs" / "requirements" / "requirements.json"
# Point to Python package metadata that must identify the same packaged release.
PYPROJECT = ROOT / "pyproject.toml"
# Accept only three-part semantic versions for packaged and module revisions.
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
# Extract the project version from the package metadata.
PROJECT_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)
# Extract historical source provenance from the package metadata.
SOURCE_BASELINE_RE = re.compile(r'^source_baseline\s*=\s*"([^"]+)"', re.MULTILINE)

# Define require_snippet to validate a human-readable canonical marker.
def require_snippet(path, snippet, description, errors):
    # Read the complete document so a marker may appear in prose or a list item.
    text = path.read_text(encoding="utf-8")
    # Record a focused drift error when the canonical marker is absent.
    if snippet not in text:
        # Append the path and marker purpose without treating other document text as canonical.
        errors.append(f"{path.relative_to(ROOT)} is missing {description}: {snippet}")

# Define validate_document_versions to compare repeated release context with the manifest.
def validate_document_versions(path, packaged_version, source_baseline, errors):
    # Require the packaged release marker used by README and starter documentation.
    require_snippet(path, f"Packaged application release: `{packaged_version}`", "packaged application release marker", errors)
    # Require historical provenance to stay visibly distinct from the packaged release.
    require_snippet(path, f"Historical source baseline: `{source_baseline}`", "historical source baseline marker", errors)
    # Require each maintained status document to direct readers to the canonical aggregate source.
    require_snippet(path, "`modules/module-manifest.json`", "canonical version-manifest reference", errors)

# Define validate_runtime_versions to compare imported runtime values with canonical metadata.
def validate_runtime_versions(data, errors):
    # Add the repository root so direct script execution can import the casino package.
    if str(ROOT) not in sys.path:
        # Prepend the root so this checkout wins over any unrelated installed package.
        sys.path.insert(0, str(ROOT))
    # Start protected imports so malformed runtime wiring produces validator diagnostics.
    try:
        # Import runtime configuration to inspect the public packaged release and configured games.
        from casino import config
        # Import the canonical runtime loader to inspect module revisions and provenance.
        from casino import module_versions
    # Convert any import or manifest-loading failure into a normal validation error.
    except Exception as exc:
        # Report the exception type and message so a broken source tree is actionable.
        errors.append(f"runtime version metadata could not be loaded: {type(exc).__name__}: {exc}")
        # Stop runtime comparisons because the required values are unavailable.
        return
    # Compare the config facade used by API and Admin surfaces with the packaged release.
    if config.APP_VERSION != data["application"]:
        # Record the exact runtime and canonical values for drift diagnosis.
        errors.append(f"casino.config APP_VERSION {config.APP_VERSION} does not match packaged release {data['application']}")
    # Compare the loader's packaged release with its canonical source.
    if module_versions.APP_VERSION != data["application"]:
        # Record duplicate or incorrectly mapped packaged-release metadata.
        errors.append(f"casino.module_versions APP_VERSION {module_versions.APP_VERSION} does not match packaged release {data['application']}")
    # Compare historical provenance without conflating it with either current version class.
    if module_versions.SOURCE_BASELINE_VERSION != data["source_baseline"]:
        # Record a source-baseline mismatch separately from packaged-release drift.
        errors.append("casino.module_versions SOURCE_BASELINE_VERSION does not match the canonical source baseline")
    # Compare the exact module key set and values used by Admin and the game registry.
    if module_versions.MODULE_REVISIONS != data["modules"]:
        # Record any stale alias, missing module, extra module, or outdated revision as one drift class.
        errors.append("casino.module_versions MODULE_REVISIONS does not exactly match canonical module revisions")
    # Build the deterministic Admin response shape expected from the canonical manifest.
    expected_rows = [{"module": module, "revision": revision} for module, revision in data["modules"].items()]
    # Compare the public Admin helper with the exact canonical order and values.
    if module_versions.list_module_revisions() != expected_rows:
        # Record response-shape or ordering drift that could otherwise escape static comparison.
        errors.append("list_module_revisions() does not return canonical module rows in manifest order")
    # Collect every configured game ID whose registry revision must exist.
    configured_games = {game["id"] for game in config.GAMES}
    # Identify game metadata omissions before runtime can fall back or fail in a request.
    missing_games = sorted(configured_games - set(data["modules"]))
    # Report every missing game module revision together for a concise failure.
    if missing_games:
        # Append the absent game IDs so maintainers know which module files to repair.
        errors.append("configured games missing canonical module revisions: " + ", ".join(missing_games))

# Define main to validate packaged-release and independent-module version policy.
def main():
    # Load the canonical aggregate manifest before checking derived surfaces.
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # Collect all drift and format errors so one run provides a complete repair list.
    errors = []
    # Read the packaged release while tolerating a missing value long enough to report it.
    packaged_version = data.get("application", "")
    # Read historical source provenance separately from the packaged release.
    source_baseline = data.get("source_baseline", "")
    # Read independent module revisions while tolerating a missing object for diagnostics.
    modules = data.get("modules", {})
    # Require the packaged application release to use semantic x.y.z form.
    if not isinstance(packaged_version, str) or not VERSION_RE.fullmatch(packaged_version):
        # Report a malformed packaged-release value.
        errors.append("packaged application release is not semantic x.y.z")
    # Require historical source provenance to remain an explicit semantic version.
    if not isinstance(source_baseline, str) or not VERSION_RE.fullmatch(source_baseline):
        # Report malformed provenance without describing it as a current release.
        errors.append("historical source baseline is not semantic x.y.z")
    # Require the canonical module mapping to remain a non-empty object.
    if not isinstance(modules, dict) or not modules:
        # Report missing module metadata before per-module checks.
        errors.append("canonical module revisions must be a non-empty object")
        # Use an empty mapping so remaining validator stages can produce useful diagnostics.
        modules = {}
    # Collect every module-specific manifest present on disk except the aggregate file.
    module_files = {path.stem: path for path in (ROOT / "modules").glob("*.json") if path.name != MANIFEST.name}
    # Identify aggregate entries without a matching module-specific manifest.
    missing_files = sorted(set(modules) - set(module_files))
    # Report missing module manifests as an exact set mismatch.
    if missing_files:
        # Append every missing file stem for one actionable error.
        errors.append("missing module manifests: " + ", ".join(missing_files))
    # Identify module-specific manifests omitted from the aggregate source.
    extra_files = sorted(set(module_files) - set(modules))
    # Report orphan module manifests so their revisions cannot escape validation.
    if extra_files:
        # Append every orphan file stem for one actionable error.
        errors.append("module manifests missing from aggregate manifest: " + ", ".join(extra_files))
    # Validate each canonical module revision and its matching module-specific record.
    for module, version in modules.items():
        # Require every independent module revision to use semantic x.y.z form.
        if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
            # Report the module name and malformed value.
            errors.append(f"module {module} version {version} is not semantic x.y.z")
        # Skip file-level checks after the exact-set diagnostic when this file is absent.
        if module not in module_files:
            # Continue to the next canonical module without raising a file error.
            continue
        # Load the module-specific ownership and revision record.
        body = json.loads(module_files[module].read_text(encoding="utf-8"))
        # Require the internal module name to match its file and aggregate key.
        if body.get("module") != module:
            # Report renamed or copied manifest metadata that could mask ownership drift.
            errors.append(f"module file {module}.json declares module {body.get('module')}")
        # Require the module-specific revision to match the aggregate source.
        if body.get("version") != version:
            # Report the existing manifest-to-file mismatch class.
            errors.append(f"module {module} version mismatch between aggregate and module file")
    # Run imported runtime comparisons only when canonical keys needed by the loader exist.
    if packaged_version and source_baseline and modules:
        # Validate API, Admin, and game-registry source values through their runtime imports.
        validate_runtime_versions(data, errors)
    # Validate both maintained human-readable version-policy surfaces.
    validate_document_versions(README, packaged_version, source_baseline, errors)
    # Validate the starter document independently so either surface can fail CI.
    validate_document_versions(STARTER, packaged_version, source_baseline, errors)
    # Require generated requirements to label the packaged release unambiguously.
    require_snippet(GENERATED_REQUIREMENTS, f"Packaged application release: {packaged_version}", "generated packaged-release marker", errors)
    # Require generated requirements to label independent module revisions unambiguously.
    require_snippet(GENERATED_REQUIREMENTS, "## Independent module revisions", "independent module revision heading", errors)
    # Read package metadata so built distributions cannot advertise a different release.
    package_text = PYPROJECT.read_text(encoding="utf-8")
    # Require wheel discovery to include the package that owns the canonical manifest file.
    if 'include = ["casino*", "modules*"]' not in package_text:
        # Report packaging drift that would make installed runtime imports fail.
        errors.append("pyproject.toml must package the modules manifest owner alongside casino")
    # Require the canonical aggregate manifest to be included as package data.
    if 'modules = ["module-manifest.json"]' not in package_text:
        # Report missing wheel data before an installed runtime can fail at import time.
        errors.append("pyproject.toml must include module-manifest.json as modules package data")
    # Extract the packaged project version from its dedicated metadata field.
    package_match = PROJECT_VERSION_RE.search(package_text)
    # Compare package metadata with the canonical packaged application release.
    if not package_match or package_match.group(1) != packaged_version:
        # Report missing or stale package metadata as packaged-release drift.
        errors.append("pyproject.toml project version does not match the packaged application release")
    # Extract historical provenance from tool metadata.
    baseline_match = SOURCE_BASELINE_RE.search(package_text)
    # Compare package provenance with the canonical historical source baseline.
    if not baseline_match or baseline_match.group(1) != source_baseline:
        # Report missing or stale provenance independently from the project version.
        errors.append("pyproject.toml source baseline does not match the canonical source baseline")
    # Load canonical requirement metadata so its provenance field follows the same policy language.
    requirements = json.loads(REQUIREMENTS.read_text(encoding="utf-8"))
    # Reject the former ambiguous release label and require explicit historical provenance.
    if requirements.get("source_baseline") != source_baseline or "release" in requirements:
        # Report requirement-registry metadata that could be mistaken for the packaged release.
        errors.append("requirements metadata must identify the canonical historical source baseline, not a release")
    # Resolve the immutable compatibility record for the current packaged release.
    compatibility_path = ROOT / "contracts" / "compatibility" / f"app-{packaged_version}.json"
    # Require a compatibility record whenever the canonical packaged release changes.
    if not compatibility_path.exists():
        # Report the expected release-specific path so a formal release cannot be partial.
        errors.append(f"missing packaged-release compatibility record: {compatibility_path.relative_to(ROOT)}")
    # Compare compatibility identity and provenance without requiring its historical module snapshot to advance.
    else:
        # Load the immutable compatibility record for identity checks.
        compatibility = json.loads(compatibility_path.read_text(encoding="utf-8"))
        # Require the record to identify the same packaged release as its canonical source.
        if compatibility.get("app_version") != packaged_version:
            # Report a mislabeled compatibility artifact.
            errors.append("compatibility record app_version does not match the packaged application release")
        # Require the record to preserve the same historical source provenance.
        if compatibility.get("source_baseline") != source_baseline:
            # Report provenance drift in the packaged-release compatibility artifact.
            errors.append("compatibility record source_baseline does not match the canonical source baseline")
    # Print a complete error list and fail when any version surface drifted.
    if errors:
        # Write a stable failure heading for CI and local validation.
        print("Version validation failed:")
        # Print each independent error so multiple stale surfaces can be fixed in one pass.
        for error in errors:
            # Prefix diagnostics consistently for readable job logs.
            print(f" - {error}")
        # Return a failing process status to the caller.
        return 1
    # Report both version classes without implying the module revision is a release.
    print(f"Version validation passed for packaged release {packaged_version} and {len(modules)} module revisions.")
    # Return success after every maintained surface aligns with canonical policy.
    return 0

# Run validation only when the script is executed directly.
if __name__ == "__main__":
    # Exit with the validator result so CI receives the correct status.
    raise SystemExit(main())
