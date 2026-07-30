"""Build and verify deterministic Casino Simulator release artifacts for TOOL-003."""

# Import argument parsing for the build and verification command-line interfaces.
import argparse
# Import UTC timestamp helpers for commit-derived deterministic provenance.
import datetime
# Import hashing primitives for artifact, manifest, and file inventories.
import hashlib
# Import JSON support for canonical release manifests and module metadata.
import json
# Import environment access for isolated extracted-copy smoke execution.
import os
# Import portable paths for repository, archive, and temporary-copy handling.
import pathlib
# Import regular expressions for immutable commit and dependency validation.
import re
# Import subprocess support for Git discovery and extracted-copy smoke checks.
import subprocess
# Import the active interpreter path for the extracted-copy smoke process.
import sys
# Import temporary directory support so smoke evidence cannot touch user data.
import tempfile
# Import TOML parsing from the Python standard library for dependency inventory.
import tomllib
# Import ZIP primitives for normalized, reproducible application archives.
import zipfile

# Resolve the repository root independently of the caller's working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Keep generated candidates under the repository's ignored distribution directory.
DIST = ROOT / "dist"
# Give the immutable application archive one stable release-asset name.
ARCHIVE_NAME = "virtual_casino_simulator_package.zip"
# Give the external checksum-bound provenance record one stable asset name.
MANIFEST_NAME = "release-manifest.json"
# Place every packaged file under one canonical extraction directory.
ARCHIVE_ROOT = "virtual_casino_simulator"
# Normalize ZIP member timestamps so equal source bytes yield equal archives.
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
# Accept only full lowercase or uppercase Git object identifiers in provenance.
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
# Allow only the runtime and audit roots required by the application artifact.
ALLOWED_PREFIXES = ("casino/", "contracts/", "deploy/", "migrations/", "modules/", "web/")
# Allow only deployable top-level files rather than repository governance content.
ALLOWED_FILES = {
    # Package the architecture overview shipped with the release for operators.
    "ARCHITECTURE.md",
    # Package the license text required for redistribution.
    "LICENSE",
    # Package the attribution notice that accompanies the license.
    "NOTICE",
    # Package the top-level readme so an extracted release is self-describing.
    "README.md",
    # Package the release notes that document the shipped version.
    "RELEASE_NOTES.md",
    # Package the project metadata consumed by the production interpreter.
    "pyproject.toml",
    # Package the one-click launcher entry point.
    "run.py",
    # Package the migration driver executed against production MySQL.
    "scripts/mysql_migrate.py",
    # Package the recovery driver invoked during application-only rollback.
    "scripts/recovery.py",
    # Package the edge gate helper executed from the extracted release.
    "scripts/edge_gate.py",
    # Package the exact extracted-release verifier invoked by production activation.
    "scripts/package_app.py",
    # Package the secret-safe monitor pairing validator invoked before cutover.
    "scripts/validate_monitor_config.py",
    # Package the non-shell monitor runner invoked after production restart.
    "scripts/run_edge_monitor.py",
    # Package the release-environment writer that installs build provenance.
    "scripts/write_release_env.py",
}
# Reject runtime, private, generated, test, and local-evidence directories anywhere.
FORBIDDEN_PARTS = {
    ".git",
    ".github",
    "__pycache__",
    "codex",
    "data",
    "dist",
    "docs",
    "evidence",
    "logs",
    "node_modules",
    "playwright-report",
    "test-results",
    "tests",
}
# Reject common credential and signing-key suffixes even inside an allowed root.
FORBIDDEN_SUFFIXES = {".key", ".p12", ".pem", ".pfx"}
# Require the minimum runtime, static, metadata, and schema surfaces in every archive.
REQUIRED_FILES = {
    "casino/__init__.py",
    "casino/app.py",
    "casino/wsgi.py",
    "deploy/acme/casino-renewal-hook.sh.template",
    "deploy/edge/restricted-preview.json",
    "deploy/gunicorn.conf.py",
    "deploy/nginx/casino.conf.template",
    "deploy/rollback/casino-edge-rollback.sh.template",
    "deploy/systemd/casino.service",
    "deploy/systemd/casino-edge-monitor.service.template",
    "deploy/systemd/casino-edge-monitor.timer.template",
    "modules/module-manifest.json",
    "pyproject.toml",
    "run.py",
    "migrations/mysql/0001_initial.json",
    "migrations/mysql/0002_action_identity.json",
    "migrations/mysql/0003_game_action_receipts.json",
    "migrations/mysql/catalog.json",
    "scripts/mysql_migrate.py",
    "scripts/recovery.py",
    "scripts/edge_gate.py",
    # Require the verifier because activation executes it from the extracted release.
    "scripts/package_app.py",
    # Require the monitor validator because it gates activation before selector mutation.
    "scripts/validate_monitor_config.py",
    # Require the non-shell monitor runner because post-cutover health invokes it.
    "scripts/run_edge_monitor.py",
    "scripts/write_release_env.py",
    "casino/core/recovery.py",
    "web/app.js",
    "web/index.html",
}


# Return a lowercase SHA-256 digest for deterministic bytes.
def sha256_bytes(payload):
    # Hash the exact byte sequence without newline or encoding normalization.
    return hashlib.sha256(payload).hexdigest()


# Execute a read-only Git query in the selected repository checkout.
def git_output(root, *arguments):
    # Capture stable text output while surfacing any Git failure to the caller.
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    # Remove only Git's terminal newline from the returned scalar value.
    return result.stdout.strip()


# Reject tracked or staged source changes before an immutable candidate is built.
def require_clean_tracked_checkout(root):
    # Ignore untracked files because the tracked-file allowlist excludes them by design.
    status = git_output(root, "status", "--porcelain", "--untracked-files=no")
    # Fail closed when packaged tracked bytes do not match the exact commit.
    if status:
        # Describe the invariant without echoing potentially private file names.
        raise ValueError("tracked checkout must be clean before release packaging")


# Return every tracked path without consulting or traversing untracked content.
def tracked_paths(root):
    # Ask Git for the authoritative tracked-file inventory using NUL separators.
    output = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    # Decode repository paths and discard the final empty separator element.
    return [item.decode("utf-8") for item in output.split(b"\0") if item]


# Decide whether a normalized repository path belongs in the application artifact.
def is_allowlisted(relative_path):
    # Accept the small top-level deployment set exactly.
    if relative_path in ALLOWED_FILES:
        # Return immediately for an explicitly named application file.
        return True
    # Accept tracked files beneath the declared runtime and audit roots.
    return relative_path.startswith(ALLOWED_PREFIXES)


# Return a secret-safety diagnostic when a candidate path is forbidden.
def forbidden_reason(relative_path):
    # Parse with POSIX separators because Git paths are platform independent.
    parts = pathlib.PurePosixPath(relative_path).parts
    # Reject path traversal, absolute paths, and empty components before filesystem access.
    if not parts or relative_path.startswith("/") or ".." in parts:
        # Explain the structural path violation without inspecting file contents.
        return "unsafe repository path"
    # Reject runtime and evidence directory names at any nesting level.
    if any(part.lower() in FORBIDDEN_PARTS for part in parts):
        # Identify the policy class rather than a host-specific path.
        return "forbidden runtime, test, or evidence directory"
    # Normalize the basename once for private-file pattern checks.
    name = parts[-1].lower()
    # Reject environment files and common private-key names.
    if name == ".env" or name.startswith(".env.") or name.startswith("id_rsa") or name.startswith("id_ed25519"):
        # Report the credential class without reading its bytes.
        return "credential-like file name"
    # Reject credential and signing-key file extensions.
    if pathlib.PurePosixPath(name).suffix in FORBIDDEN_SUFFIXES:
        # Report the suffix policy without disclosing file contents.
        return "credential-like file suffix"
    # Permit the path when no private or generated pattern matched.
    return None


# Select existing regular tracked files using an explicit fail-closed allowlist.
def select_release_files(root, repository_paths):
    # Accumulate normalized source paths in deterministic lexical order.
    selected = []
    # Deduplicate caller input before evaluating each tracked repository path.
    for relative_path in sorted(set(repository_paths)):
        # Skip repository content that is not part of the deployable allowlist.
        if not is_allowlisted(relative_path):
            # Continue without statting or reading an untracked or out-of-scope path.
            continue
        # Reject private, runtime, and generated names even beneath allowed roots.
        reason = forbidden_reason(relative_path)
        # Safely omit known non-runtime directories that can exist beneath application roots.
        if reason == "forbidden runtime, test, or evidence directory":
            # Continue without reading documentation evidence or generated content bytes.
            continue
        # Fail closed rather than silently omitting a suspicious tracked runtime file.
        if reason:
            # Name only the repository-relative path in the developer diagnostic.
            raise ValueError(f"refusing allowlisted path {relative_path}: {reason}")
        # Resolve the tracked source path only after path-policy validation.
        source = root / pathlib.PurePosixPath(relative_path)
        # Reject symlinks so an archive cannot escape the clean checkout boundary.
        if source.is_symlink():
            # Report the safe repository-relative path for remediation.
            raise ValueError(f"release path must not be a symlink: {relative_path}")
        # Require every allowlisted tracked entry to remain a regular file.
        if not source.is_file():
            # Fail when Git metadata and working-tree file types diverge.
            raise ValueError(f"tracked release path is not a regular file: {relative_path}")
        # Retain the validated repository-relative path for archive construction.
        selected.append(relative_path)
    # Compute mandatory application surfaces absent from the selected file set.
    missing = sorted(REQUIRED_FILES - set(selected))
    # Reject incomplete artifacts before writing any archive bytes.
    if missing:
        # List only canonical repository paths that maintainers must restore.
        raise ValueError("release allowlist is missing required files: " + ", ".join(missing))
    # Return a stable path sequence for deterministic ZIP ordering.
    return selected


# Read canonical package metadata and produce a deterministic dependency inventory.
def project_inventory(root):
    # Parse package metadata with the standard library instead of lossy text matching.
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    # Start with direct runtime dependencies declared by the packaged project.
    components = [
        {"requirement": requirement, "scope": "runtime"}
        for requirement in sorted(project.get("dependencies", []))
    ]
    # Add each optional dependency group with an explicit reproducibility scope.
    for group, requirements in sorted(project.get("optional-dependencies", {}).items()):
        # Append stable requirement strings without resolving network-dependent versions.
        components.extend(
            {"requirement": requirement, "scope": f"optional:{group}"}
            for requirement in sorted(requirements)
        )
    # Read the development lock inputs used by the validation workflow when present.
    dev_path = root / "requirements-dev.txt"
    # Keep non-empty, non-comment requirement lines as declared validation dependencies.
    dev_requirements = [
        line.strip()
        for line in dev_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ] if dev_path.exists() else []
    # Add stable development requirements after runtime and optional dependencies.
    components.extend(
        {"requirement": requirement, "scope": "development"}
        for requirement in sorted(dev_requirements)
    )
    # Return canonical release identity, Python support, and a lightweight SBOM payload.
    return {
        "name": project["name"],
        "version": project["version"],
        "requires_python": project["requires-python"],
        "sbom": {
            "components": components,
            "format": "casino-release-sbom-v1",
        },
    }


# Return checksum-verified MySQL schema compatibility for release provenance.
def mysql_schema_inventory(root):
    # Resolve the canonical migration catalog inside the selected source tree.
    catalog_path = root / "migrations" / "mysql" / "catalog.json"
    # Read exact catalog bytes for release binding.
    catalog_bytes = catalog_path.read_bytes()
    # Parse expected/minimum versions and immutable migration rows.
    catalog = json.loads(catalog_bytes.decode("utf-8"))
    # Require the reviewed catalog format.
    if catalog.get("schema") != "casino-mysql-migration-catalog-v1":
        # Reject an unknown migration provenance format.
        raise ValueError("MySQL migration catalog format is unsupported")
    # Parse exact runtime compatibility independently of application schema metadata.
    expected = int(catalog.get("expected_version", -1))
    # Parse the minimum compatible MySQL migration version.
    minimum = int(catalog.get("minimum_runtime_version", -1))
    # Require one closed runtime window within the complete packaged catalog.
    if expected < 1 or minimum < 1 or minimum > expected:
        # Refuse an empty, inverted, or unbounded compatibility range.
        raise ValueError("MySQL migration compatibility window is invalid")
    # Require the manifest-bound bridge policy to keep migration execution closed.
    if catalog.get("apply_policy") != "held":
        # Reject a catalog that silently enables schema application.
        raise ValueError("MySQL migration apply policy is invalid")
    # Accumulate the exact migration identity chain.
    rows = []
    # Verify every catalog row and referenced tracked file.
    for index, row in enumerate(catalog.get("migrations", []), start=1):
        # Require contiguous order and exact expected tail.
        if int(row.get("version", -1)) != index:
            # Reject gapped release provenance.
            raise ValueError("MySQL migration catalog is not contiguous")
        # Accept only one catalog-directory basename matching its numeric version.
        if not re.fullmatch(rf"{index:04d}_[a-z0-9_]+\.json", str(row.get("file", ""))):
            # Reject traversal and mismatched file identity.
            raise ValueError("MySQL migration filename is invalid")
        # Read exact migration bytes beside the catalog.
        payload = (catalog_path.parent / str(row.get("file", ""))).read_bytes()
        # Require the file checksum to match immutable catalog metadata.
        if row.get("sha256") != sha256_bytes(payload):
            # Reject edited migration files before packaging.
            raise ValueError("MySQL migration checksum does not match the catalog")
        # Retain only version, stable name, and exact checksum.
        rows.append([index, str(row.get("name", "")), str(row["sha256"])])
    # Require the expected version to match the final migration exactly.
    if len(rows) != expected:
        # Refuse incomplete migration packaging.
        raise ValueError("MySQL migration catalog tail does not match expected version")
    # Return a deterministic public schema record with no connection details.
    return {
        # Bind exact catalog bytes.
        "catalog_sha256": sha256_bytes(catalog_bytes),
        # Record the exact schema expected by this release.
        "expected_version": expected,
        # Record the minimum compatible schema independently.
        "minimum_version": minimum,
        # Bind the complete ordered migration chain.
        "migration_chain_sha256": sha256_bytes(json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode("utf-8")),
        # Bind the closed migration-application policy.
        "apply_policy": "held",
    }


# Validate the exact application-only/no-database-rollback compatibility tuple.
def compatibility_rollback_schema(rollback):
    # Require exactly the four governed rollback fields and no shadow policy.
    expected_keys = {"scope", "database_rollback", "mysql_expected_schema_version", "requires_retained_predecessor_manifest"}
    # Reject missing, extra, or non-object rollback declarations.
    if not isinstance(rollback, dict) or set(rollback) != expected_keys:
        # Fail publication without the complete governed boundary.
        raise ValueError("release rollback policy declaration is invalid")
    # Require the application-only rollback scope.
    if rollback.get("scope") != "application-only":
        # Reject any broader restoration authority.
        raise ValueError("release rollback policy declaration is invalid")
    # Require database rollback to remain explicitly prohibited.
    if rollback.get("database_rollback") != "prohibited":
        # Prevent a packaged record from authorizing database mutation.
        raise ValueError("release rollback policy declaration is invalid")
    # Require the exact retained predecessor manifest boundary.
    if rollback.get("requires_retained_predecessor_manifest") is not True:
        # Refuse a waiver or missing retained-artifact requirement.
        raise ValueError("release rollback policy declaration is invalid")
    # Preserve the exact database version expected during application rollback.
    schema_version = rollback.get("mysql_expected_schema_version")
    # Reject booleans and nonpositive or noninteger declarations.
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version < 1:
        # Keep the failure independent of record content or path.
        raise ValueError("release rollback schema declaration is invalid")
    # Return the reviewed exact rollback database version.
    return schema_version


# Read the candidate compatibility record's exact rollback database version.
def rollback_schema_version(root, current_version):
    # Resolve only the governed compatibility record for this packaged version.
    record_path = root / "contracts" / "compatibility" / f"app-{current_version}.json"
    # Parse the tracked candidate policy before writing release assets.
    record = json.loads(record_path.read_text(encoding="utf-8"))
    # Require the record identity to match the packaged version.
    if record.get("app_version") != current_version:
        # Reject copied or stale rollback policy.
        raise ValueError("release compatibility identity does not match application version")
    # Validate the complete governed rollback tuple before consuming its version.
    return compatibility_rollback_schema(record.get("rollback"))


# Require one declared database version to fall inside a closed runtime window.
def require_schema_window(schema_version, schema_record, label):
    # Require the manifest schema record to remain a mapping.
    if not isinstance(schema_record, dict):
        # Refuse missing candidate or predecessor schema provenance.
        raise ValueError(f"{label} MySQL schema window is missing")
    # Read exact non-boolean integer bounds.
    minimum = schema_record.get("minimum_version")
    # Read the maximum packaged schema version independently.
    expected = schema_record.get("expected_version")
    # Reject malformed or inverted schema bounds.
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (minimum, expected)) or minimum < 1 or minimum > expected:
        # Preserve one fixed window diagnostic.
        raise ValueError(f"{label} MySQL schema window is invalid")
    # Require the declared rollback database to be runnable by the release.
    if schema_version < minimum or schema_version > expected:
        # Prevent an application rollback that cannot pass runtime readiness.
        raise ValueError(f"{label} release cannot run against declared rollback MySQL schema")


# Convert an optional prior manifest into application-only rollback provenance.
def rollback_provenance(previous_manifest, current_version, candidate_schema, schema_version):
    # Require the candidate itself to accept the declared rollback database version.
    require_schema_window(schema_version, candidate_schema, "candidate")
    # Block immutable promotion when no retained prior artifact was supplied.
    if previous_manifest is None:
        # Return an explicit fail-closed mapping for ordinary branch candidates.
        return {
            "application_only": True,
            "database_rollback": "outside-TOOL-003",
            "eligible": False,
            "mysql_schema_version": schema_version,
            "previous": None,
            "reason": "A verified previous release manifest is required before immutable publication.",
        }
    # Read the exact previous manifest bytes so their checksum can be retained.
    previous_bytes = previous_manifest.read_bytes()
    # Parse the prior record only after capturing its immutable byte digest.
    previous = json.loads(previous_bytes.decode("utf-8"))
    # Extract the minimum checksum-bound identity required for rollback selection.
    try:
        # Build a compact pointer without copying prior validation or file inventories.
        pointer = {
            "app_version": previous["app_version"],
            "artifact_name": previous["artifact"]["name"],
            "artifact_sha256": previous["artifact"]["sha256"],
            "commit_sha": previous["source"]["commit_sha"],
            "manifest_sha256": sha256_bytes(previous_bytes),
            "mysql_minimum_version": previous["mysql_schema"]["minimum_version"],
            "mysql_expected_version": previous["mysql_schema"]["expected_version"],
        }
    # Convert malformed or legacy prior records into a safe release-blocking error.
    except (KeyError, TypeError) as exc:
        # Preserve the missing key name without exposing external or local paths.
        raise ValueError(f"previous release manifest is incomplete: {exc}") from exc
    # Prevent a new immutable release from naming itself as its rollback target.
    if pointer["app_version"] == current_version:
        # Require the immediately previous distinct packaged version instead.
        raise ValueError("previous release manifest must identify a different application version")
    # Require the retained predecessor runtime to accept the same database version.
    require_schema_window(schema_version, previous.get("mysql_schema"), "predecessor")
    # Return a testable application-only rollback mapping with database work excluded.
    return {
        "application_only": True,
        "database_rollback": "outside-TOOL-003",
        "eligible": True,
        "mysql_schema_version": schema_version,
        "previous": pointer,
        "reason": None,
    }


# Write normalized archive bytes and return the complete packaged-file inventory.
def write_archive(root, archive_path, release_files):
    # Replace only the known ignored output asset from an earlier local candidate.
    if archive_path.exists():
        # Remove stale bytes so ZIP append behavior cannot affect determinism.
        archive_path.unlink()
    # Collect manifest rows in the same stable order as ZIP members.
    inventory = []
    # Open a new archive with fixed compression settings and ZIP64 support.
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as archive:
        # Add each validated tracked file in lexical repository order.
        for relative_path in release_files:
            # Read exact source bytes without newline or text-encoding normalization.
            payload = (root / pathlib.PurePosixPath(relative_path)).read_bytes()
            # Build the canonical member path beneath the single extraction root.
            archive_path_name = f"{ARCHIVE_ROOT}/{relative_path}"
            # Create normalized ZIP metadata instead of inheriting host timestamps or modes.
            info = zipfile.ZipInfo(archive_path_name, date_time=ZIP_TIMESTAMP)
            # Identify the archive as Unix-authored for deterministic permission semantics.
            info.create_system = 3
            # Store every source entry as a non-executable regular file with mode 0644.
            info.external_attr = 0o100644 << 16
            # Apply the chosen deterministic compression algorithm to this member.
            info.compress_type = zipfile.ZIP_DEFLATED
            # Write bytes directly so host filesystem metadata cannot enter the archive.
            archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            # Record the complete source and archive identity for verification.
            inventory.append(
                {
                    "archive_path": archive_path_name,
                    "path": relative_path,
                    "sha256": sha256_bytes(payload),
                    "size": len(payload),
                }
            )
    # Return every packaged-file hash after the archive has closed successfully.
    return inventory


# Build one deterministic archive and its external checksum-bound manifest.
def build_release(root, dist, repository_paths, commit_sha, commit_epoch, release_tag=None, validations=None, previous_manifest=None):
    # Require an exact immutable source identifier before writing provenance.
    if not COMMIT_RE.fullmatch(commit_sha):
        # Reject shortened, symbolic, or malformed commit references.
        raise ValueError("release commit must be a full 40-character Git SHA")
    # Load canonical package and dependency metadata from the selected source tree.
    project = project_inventory(root)
    # Load the aggregate module manifest used by runtime and release policy.
    modules = json.loads((root / "modules" / "module-manifest.json").read_text(encoding="utf-8"))
    # Load checksum-verified MySQL schema compatibility for this exact source tree.
    mysql_schema = mysql_schema_inventory(root)
    # Require package metadata and the canonical packaged release to agree.
    if project["version"] != modules["application"]:
        # Stop before an artifact could carry divergent application versions.
        raise ValueError("pyproject version does not match canonical packaged application release")
    # Require release tags to be the canonical immutable version tag when supplied.
    if release_tag is not None and release_tag != f"v{project['version']}":
        # Reject user-supplied or release-event labels that diverge from metadata.
        raise ValueError(f"release tag must be v{project['version']}")
    # Select only explicit allowlisted tracked files and reject suspicious tracked names.
    release_files = select_release_files(root, repository_paths)
    # Recreate the ignored output directory without touching source or runtime state.
    dist.mkdir(parents=True, exist_ok=True)
    # Resolve the two stable release-asset paths.
    archive_path = dist / ARCHIVE_NAME
    # Resolve the external manifest path beside the application archive.
    manifest_path = dist / MANIFEST_NAME
    # Write deterministic archive bytes and capture every included-file digest.
    inventory = write_archive(root, archive_path, release_files)
    # Read final archive bytes once for checksum and size binding.
    archive_bytes = archive_path.read_bytes()
    # Convert the source commit epoch into a deterministic UTC provenance timestamp.
    source_timestamp = datetime.datetime.fromtimestamp(int(commit_epoch), tz=datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    # Read the exact database version declared by governed rollback policy.
    rollback_schema = rollback_schema_version(root, project["version"])
    # Build application-only rollback provenance from both runtime windows.
    rollback = rollback_provenance(previous_manifest, project["version"], mysql_schema, rollback_schema)
    # Record validators as deterministic passed assertions executed by make_release.py.
    validation_rows = [
        {"command": command, "status": "passed"}
        for command in (validations or [])
    ]
    # Assemble one canonical JSON provenance object with stable keys and values.
    manifest = {
        "app_version": project["version"],
        "artifact": {
            "name": ARCHIVE_NAME,
            "sha256": sha256_bytes(archive_bytes),
            "size": len(archive_bytes),
        },
        "build": {
            "archive_member_timestamp": "1980-01-01T00:00:00Z",
            "source_timestamp": source_timestamp,
            "timestamp_policy": "Git commit time records provenance; ZIP member metadata is normalized.",
        },
        "files": inventory,
        "modules": modules,
        "mysql_schema": mysql_schema,
        "promotion": {
            "immutable_publication_eligible": bool(release_tag and rollback["eligible"]),
            "required_event": "published release on a protected canonical version tag",
        },
        "rollback": rollback,
        "runtime": {
            "requires_python": project["requires_python"],
        },
        "schema_version": 1,
        "sbom": project["sbom"],
        "source": {
            "commit_sha": commit_sha.lower(),
            "release_tag": release_tag,
        },
        "validations": validation_rows,
    }
    # Serialize with sorted keys and a single trailing newline for byte reproducibility.
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    # Replace only the stable ignored manifest asset from an earlier local candidate.
    manifest_path.write_text(manifest_text, encoding="utf-8", newline="\n")
    # Return both release assets for follow-up verification and checksum generation.
    return archive_path, manifest_path


# Run a listener-free import and static-asset smoke from a clean extracted copy.
def smoke_extracted_copy(extracted_root, expected_version):
    # Define a compact child program that exercises imports and startup metadata only.
    smoke_program = (
        "import json, pathlib; "
        "root = pathlib.Path.cwd(); "
        "manifest = json.loads((root / 'modules/module-manifest.json').read_text(encoding='utf-8')); "
        "assert manifest['application'] == __import__('sys').argv[1]; "
        "assert (root / 'web/index.html').is_file(); "
        "from casino import app, config; "
        "from casino.core import recovery; "
        "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; "
        "assert recovery.ENCRYPTED_STREAM_SCHEMA == 'casino-aes-256-gcm-chunked-v1'; "
        "assert AESGCM is not None; "
        "from scripts import edge_gate; "
        "assert edge_gate.validate_policy()['stage'] == 'repository-preparation-only'; "
        "assert callable(app.main); "
        "assert config.APP_VERSION == __import__('sys').argv[1]"
    )
    # Copy the environment so only bytecode and storage locations need isolation.
    environment = os.environ.copy()
    # Prevent extracted-copy imports from writing Python cache files.
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    # Point any defensive runtime data lookup at a temporary non-user directory.
    environment["CASINO_DATA_DIR"] = str(extracted_root / ".smoke-data")
    # Execute the supported interpreter without starting the HTTP server or a listener.
    subprocess.run(
        [sys.executable, "-c", smoke_program, expected_version],
        cwd=extracted_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


# Verify artifact checksum, inventory, metadata, rollback, and optional clean-copy smoke.
def verify_release(archive_path, manifest_path, expected_commit=None, expected_tag=None, require_rollback=False, smoke=True):
    # Load the external provenance record that binds the application archive.
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Read exact archive bytes for top-level checksum and size verification.
    archive_bytes = archive_path.read_bytes()
    # Reject a renamed or substituted archive before extraction.
    if manifest["artifact"]["name"] != archive_path.name:
        # Fail closed when the manifest names a different immutable asset.
        raise ValueError("release manifest artifact name does not match archive")
    # Reject any archive-byte change relative to the external provenance record.
    if manifest["artifact"]["sha256"] != sha256_bytes(archive_bytes):
        # Report checksum mismatch without exposing archive content.
        raise ValueError("release archive checksum does not match manifest")
    # Reject truncated or extended archives even if a caller skipped checksum comparison.
    if manifest["artifact"]["size"] != len(archive_bytes):
        # Report the invariant rather than host-specific file details.
        raise ValueError("release archive size does not match manifest")
    # Enforce an exact expected source commit when the caller supplies one.
    if expected_commit is not None and manifest["source"]["commit_sha"] != expected_commit.lower():
        # Stop publication when checked-out source and artifact provenance differ.
        raise ValueError("release manifest commit does not match expected commit")
    # Enforce an exact canonical release tag when the caller supplies one.
    if expected_tag is not None and manifest["source"]["release_tag"] != expected_tag:
        # Stop publication when release-event identity and provenance diverge.
        raise ValueError("release manifest tag does not match expected tag")
    # Require a retained prior artifact before immutable publication.
    if require_rollback and not manifest["rollback"]["eligible"]:
        # Preserve branch candidate usability while making publication fail closed.
        raise ValueError("immutable publication requires eligible rollback provenance")
    # Build the expected member map from the complete manifest inventory.
    expected_members = {row["archive_path"]: row for row in manifest["files"]}
    # Open the archive for structural, metadata, and content verification.
    with zipfile.ZipFile(archive_path, "r") as archive:
        # Capture each member once to reject duplicates and unrecorded content.
        members = archive.infolist()
        # Reject duplicate member names that could overwrite on extraction.
        if len({member.filename for member in members}) != len(members):
            # Stop before extracting an ambiguous archive.
            raise ValueError("release archive contains duplicate members")
        # Require the archive member set to match the manifest exactly.
        if {member.filename for member in members} != set(expected_members):
            # Reject both omitted manifest rows and hidden archive additions.
            raise ValueError("release archive inventory does not match manifest")
        # Verify every member's path, normalized metadata, bytes, and hash.
        for member in members:
            # Parse member paths with POSIX semantics mandated by ZIP.
            parts = pathlib.PurePosixPath(member.filename).parts
            # Reject absolute or traversal paths before any extraction occurs.
            if not parts or parts[0] != ARCHIVE_ROOT or ".." in parts:
                # Stop on a member that could escape or bypass the extraction root.
                raise ValueError("release archive contains an unsafe member path")
            # Require the deterministic timestamp used by the writer.
            if member.date_time != ZIP_TIMESTAMP:
                # Detect host-metadata leakage or noncanonical repackaging.
                raise ValueError("release archive member timestamp is not normalized")
            # Read the exact uncompressed member bytes for checksum verification.
            payload = archive.read(member.filename)
            # Compare byte length with the external complete-file inventory.
            if len(payload) != expected_members[member.filename]["size"]:
                # Detect truncated or expanded member content.
                raise ValueError("release archive member size does not match manifest")
            # Compare member bytes with the external SHA-256 inventory.
            if sha256_bytes(payload) != expected_members[member.filename]["sha256"]:
                # Detect any substituted packaged file.
                raise ValueError("release archive member checksum does not match manifest")
        # Read the already authenticated migration catalog from the archive.
        catalog_member = f"{ARCHIVE_ROOT}/migrations/mysql/catalog.json"
        # Parse exact packaged catalog bytes.
        catalog_bytes = archive.read(catalog_member)
        # Decode the reviewed migration catalog.
        catalog = json.loads(catalog_bytes.decode("utf-8"))
        # Require the accepted catalog format.
        if catalog.get("schema") != "casino-mysql-migration-catalog-v1":
            # Reject substituted schema metadata.
            raise ValueError("release MySQL migration catalog format is unsupported")
        # Parse packaged exact and minimum versions before trusting manifest values.
        packaged_expected = int(catalog.get("expected_version", -1))
        # Parse the independent minimum runtime-compatible version.
        packaged_minimum = int(catalog.get("minimum_runtime_version", -1))
        # Require one closed runtime window inside the complete packaged catalog.
        if packaged_expected < 1 or packaged_minimum < 1 or packaged_minimum > packaged_expected:
            # Reject a coherently re-signed but invalid compatibility range.
            raise ValueError("release MySQL migration compatibility window is invalid")
        # Require the packaged catalog to bind the closed bridge apply policy.
        if catalog.get("apply_policy") != "held":
            # Reject a coherently re-signed migration-enabling catalog.
            raise ValueError("release MySQL migration apply policy is invalid")
        # Collect exact packaged migration identities.
        rows = []
        # Verify every catalog checksum against authenticated archive bytes.
        for index, row in enumerate(catalog.get("migrations", []), start=1):
            # Require contiguous packaged migration versions.
            if int(row.get("version", -1)) != index:
                # Reject gapped packaged schema provenance.
                raise ValueError("release MySQL migration catalog is not contiguous")
            # Accept only a basename tied to the contiguous numeric version.
            if not re.fullmatch(rf"{index:04d}_[a-z0-9_]+\.json", str(row.get("file", ""))):
                # Reject traversal or mismatched migration members.
                raise ValueError("release MySQL migration filename is invalid")
            # Read the exact catalog-selected migration member.
            migration_payload = archive.read(f"{ARCHIVE_ROOT}/migrations/mysql/{row['file']}")
            # Require catalog and packaged migration checksums to agree.
            if row.get("sha256") != sha256_bytes(migration_payload):
                # Reject an internally inconsistent schema artifact.
                raise ValueError("release MySQL migration checksum is invalid")
            # Retain the exact ordered migration identity.
            rows.append([index, str(row.get("name", "")), str(row["sha256"])])
        # Require the catalog tail to match the expected version exactly.
        if len(rows) != packaged_expected:
            # Reject a coherent manifest and catalog with an incomplete tail.
            raise ValueError("release MySQL migration catalog tail does not match expected version")
        # Build the schema provenance implied by packaged bytes.
        packaged_schema = {
            # Bind exact packaged catalog bytes.
            "catalog_sha256": sha256_bytes(catalog_bytes),
            # Preserve the catalog's exact version.
            "expected_version": packaged_expected,
            # Preserve the catalog's minimum version.
            "minimum_version": packaged_minimum,
            # Bind the complete ordered packaged chain.
            "migration_chain_sha256": sha256_bytes(json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode("utf-8")),
            # Bind the closed migration-application policy.
            "apply_policy": "held",
        }
        # Require the external manifest to match packaged catalog and migrations exactly.
        if manifest.get("mysql_schema") != packaged_schema:
            # Reject divergent release schema expectations.
            raise ValueError("release manifest MySQL schema provenance does not match archive")
        # Resolve the authenticated packaged compatibility record for this application version.
        compatibility_member = f"{ARCHIVE_ROOT}/contracts/compatibility/app-{manifest['app_version']}.json"
        # Require the compatibility record to be part of the authenticated inventory.
        if compatibility_member not in expected_members:
            # Reject an archive that omits governed rollback schema policy.
            raise ValueError("release packaged compatibility record is missing")
        # Parse the already inventory- and checksum-verified compatibility bytes.
        try:
            # Decode the exact packaged policy object.
            packaged_compatibility = json.loads(archive.read(compatibility_member).decode("utf-8"))
        # Normalize malformed or undecodable policy bytes.
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            # Preserve no packaged content in the diagnostic.
            raise ValueError("release packaged compatibility record is invalid") from exc
        # Require the packaged policy identity to match the manifest application.
        if not isinstance(packaged_compatibility, dict) or packaged_compatibility.get("app_version") != manifest["app_version"]:
            # Reject copied, malformed, or stale packaged rollback policy.
            raise ValueError("release compatibility identity does not match manifest")
        # Read the packaged rollback policy only after its bytes are authenticated.
        packaged_rollback = packaged_compatibility.get("rollback")
        # Require the governed rollback declaration to remain an object.
        if not isinstance(packaged_rollback, dict):
            # Refuse an artifact without packaged rollback schema policy.
            raise ValueError("release compatibility rollback declaration is invalid")
        # Validate the complete policy and read its exact rollback database version.
        packaged_rollback_schema = compatibility_rollback_schema(packaged_rollback)
        # Read the manifest-bound rollback mapping only after schema provenance is authenticated.
        rollback = manifest.get("rollback")
        # Require the governed rollback record to remain an object.
        if not isinstance(rollback, dict):
            # Refuse an artifact without a database compatibility decision.
            raise ValueError("release rollback provenance is invalid")
        # Read the exact database version retained during application rollback.
        rollback_schema = rollback.get("mysql_schema_version")
        # Reject noninteger or boolean schema declarations.
        if isinstance(rollback_schema, bool) or not isinstance(rollback_schema, int):
            # Preserve a fixed manifest-shape diagnostic.
            raise ValueError("release rollback schema declaration is invalid")
        # Require manifest provenance to equal the authenticated packaged policy.
        if rollback_schema != packaged_rollback_schema:
            # Reject a coherently re-signed rollback-version substitution.
            raise ValueError("release rollback schema does not match packaged compatibility")
        # Require the candidate runtime to accept the declared database version.
        require_schema_window(rollback_schema, packaged_schema, "candidate")
        # Validate predecessor runtime bounds whenever rollback is eligible.
        if rollback.get("eligible"):
            # Require the compact predecessor pointer used during trusted rollback.
            previous = rollback.get("previous")
            # Reject a missing or malformed predecessor pointer.
            if not isinstance(previous, dict):
                # Preserve immutable-publication refusal.
                raise ValueError("release rollback predecessor is invalid")
            # Reconstruct only the predecessor runtime window from manifest-bound values.
            predecessor_schema = {"minimum_version": previous.get("mysql_minimum_version"), "expected_version": previous.get("mysql_expected_version")}
            # Require the predecessor to run against the same retained database version.
            require_schema_window(rollback_schema, predecessor_schema, "predecessor")
        # Run smoke only after every path and byte has been authenticated.
        if smoke:
            # Create a disposable clean target outside the repository and user runtime data.
            with tempfile.TemporaryDirectory(prefix="casino-release-smoke-") as temporary:
                # Extract the already-validated archive into the disposable directory.
                archive.extractall(temporary)
                # Resolve the canonical single archive root for smoke execution.
                extracted_root = pathlib.Path(temporary) / ARCHIVE_ROOT
                # Exercise imports, canonical version metadata, and static assets without a listener.
                smoke_extracted_copy(extracted_root, manifest["app_version"])
    # Return the verified manifest for callers that need exact release identity.
    return manifest


# Parse command-line options for building or independently verifying release assets.
def parse_args():
    # Describe the fail-closed TOOL-003 release artifact utility.
    parser = argparse.ArgumentParser(description="Build or verify deterministic Casino Simulator release artifacts.")
    # Select independent verification of existing assets instead of a new build.
    parser.add_argument("--verify-only", action="store_true")
    # Bind a candidate to the canonical protected release tag when applicable.
    parser.add_argument("--release-tag")
    # Supply the retained prior manifest required for rollback-eligible publication.
    parser.add_argument("--previous-manifest", type=pathlib.Path)
    # Record each deterministic validation command already completed by the release driver.
    parser.add_argument("--validation", action="append", default=[])
    # Override the archive path only for independent verification.
    parser.add_argument("--archive", type=pathlib.Path, default=DIST / ARCHIVE_NAME)
    # Override the manifest path only for independent verification.
    parser.add_argument("--manifest", type=pathlib.Path, default=DIST / MANIFEST_NAME)
    # Require the verified manifest to bind a caller-selected full source commit.
    parser.add_argument("--expected-commit")
    # Require the verified manifest to bind a caller-selected canonical release tag.
    parser.add_argument("--expected-tag")
    # Fail verification when the application-only prior-artifact mapping is absent.
    parser.add_argument("--require-rollback", action="store_true")
    # Permit focused tests to skip child-process smoke while retaining structural checks.
    parser.add_argument("--skip-smoke", action="store_true")
    # Return the validated command-line namespace.
    return parser.parse_args()


# Build or verify release assets without mutating source, runtime data, or listeners.
def main():
    # Parse caller intent before querying Git or reading release assets.
    args = parse_args()
    # Handle independent verification for publication and rollback gates.
    if args.verify_only:
        # Verify exact assets and any caller-required immutable identities.
        manifest = verify_release(
            args.archive,
            args.manifest,
            expected_commit=args.expected_commit,
            expected_tag=args.expected_tag,
            require_rollback=args.require_rollback,
            smoke=not args.skip_smoke,
        )
        # Report only sanitized release identity and successful verification.
        print(f"Verified release {manifest['app_version']} from {manifest['source']['commit_sha']}")
        # Return success after every requested verification gate passes.
        return 0
    # Require tracked source bytes to match the exact Git commit before packaging.
    require_clean_tracked_checkout(ROOT)
    # Resolve the immutable full source commit from the clean checkout.
    commit_sha = git_output(ROOT, "rev-parse", "HEAD")
    # Resolve the commit timestamp used by deterministic provenance policy.
    commit_epoch = git_output(ROOT, "show", "-s", "--format=%ct", "HEAD")
    # Resolve the previous manifest path only when the caller supplied one.
    previous_manifest = args.previous_manifest.resolve() if args.previous_manifest else None
    # Build the deterministic archive and checksum-bound external manifest.
    archive_path, manifest_path = build_release(
        ROOT,
        DIST,
        tracked_paths(ROOT),
        commit_sha,
        commit_epoch,
        release_tag=args.release_tag,
        validations=args.validation,
        previous_manifest=previous_manifest,
    )
    # Verify bytes, inventory, provenance, and clean-copy imports before reporting success.
    manifest = verify_release(archive_path, manifest_path, expected_commit=commit_sha, expected_tag=args.release_tag)
    # Report stable relative asset names without revealing host-specific paths.
    print(f"Wrote deterministic release {manifest['app_version']}: {archive_path.name}, {manifest_path.name}")
    # Return success after build and listener-free smoke verification.
    return 0


# Run the command-line interface only when this module is executed directly.
if __name__ == "__main__":
    # Exit with the explicit result so CI observes fail-closed behavior.
    raise SystemExit(main())
