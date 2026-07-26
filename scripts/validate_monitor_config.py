"""Validate or explicitly repair the production monitor bearer/digest pairing.

The raw bearer remains only in the root-managed monitor environment file. This tool reads it in
memory, compares its SHA-256 digest with the application environment, and never prints either value.
The optional repair mode atomically updates only the digest assignment while preserving unrelated
configuration, ownership, and permissions.
"""

# Import command-line parsing for owner-operated validation and repair.
import argparse
# Import constant-time comparison and SHA-256 derivation for the split credential.
import hashlib
# Import constant-time digest comparison for the authentication boundary.
import hmac
# Import operating-system primitives for atomic replacement and ownership preservation.
import os
# Import paths for the two root-managed environment files.
import pathlib
# Import strict assignment, bearer, and digest validation.
import re
# Import permission-bit extraction for repair preservation.
import stat
# Import bounded error reporting for secret-safe operator output.
import sys
# Import same-directory temporary files for atomic configuration replacement.
import tempfile

# Name the monitor-only raw Authorization setting.
AUTHORIZATION_ENV = "CASINO_EDGE_MONITOR_AUTHORIZATION"
# Name the application-only token digest setting.
DIGEST_ENV = "CASINO_EDGE_MONITOR_TOKEN_SHA256"
# Accept only simple environment assignments used by the systemd EnvironmentFile inputs.
ASSIGNMENT_RE = re.compile(r"^(?:export[ \t]+)?([A-Z][A-Z0-9_]*)=(.*)$")
# Require a printable, space-free, sufficiently strong bearer token without reflecting it.
AUTHORIZATION_RE = re.compile(r"^Bearer ([\x21-\x7e]{32,512})$")
# Require the application's canonical lowercase SHA-256 representation.
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


# Read one exact environment assignment and reject duplicate or malformed target rows.
def read_assignment(path: pathlib.Path, name: str) -> str:
    # Decode the root-managed environment file without shell evaluation.
    lines = path.read_text(encoding="utf-8").splitlines()
    # Start with no accepted value so duplicates fail closed.
    found = None
    # Inspect each physical line independently to reject multiline interpretation.
    for line in lines:
        # Ignore blank and whole-line comment rows.
        if not line.strip() or line.lstrip().startswith("#"):
            # Continue without interpreting comment contents.
            continue
        # Parse only a simple assignment shape and never source shell syntax.
        match = ASSIGNMENT_RE.fullmatch(line)
        # Ignore unrelated well-formed environment settings.
        if match and match.group(1) != name:
            # Preserve separation between monitor and application configuration.
            continue
        # Reject a malformed row that appears to target the protected setting.
        if not match and line.lstrip().startswith(name):
            # Fail before token or digest derivation.
            raise ValueError("protected assignment malformed")
        # Continue past unrelated malformed rows because this tool owns only one setting per file.
        if not match:
            # Leave other configuration validation to the service's established loader.
            continue
        # Reject duplicate protected assignments whose shell precedence would be ambiguous.
        if found is not None:
            # Fail closed without reflecting either value.
            raise ValueError("protected assignment duplicated")
        # Capture the exact unquoted value used by the existing root-managed file format.
        found = match.group(2)
    # Require the protected assignment to be present.
    if found is None:
        # Reject incomplete monitor setup.
        raise ValueError("protected assignment missing")
    # Return the in-memory value without logging it.
    return found


# Derive the monitor token digest from the root-managed Authorization assignment.
def expected_digest(monitor_path: pathlib.Path) -> str:
    # Read the exact monitor Authorization value.
    authorization = read_assignment(monitor_path, AUTHORIZATION_ENV)
    # Require the fixed Bearer scheme and a strong, space-free token.
    match = AUTHORIZATION_RE.fullmatch(authorization)
    # Reject malformed authorization without printing it.
    if not match:
        # Keep the failure category independent of secret content.
        raise ValueError("monitor authorization invalid")
    # Hash only the token bytes because the application verifies the bearer payload, not the scheme.
    return hashlib.sha256(match.group(1).encode("utf-8")).hexdigest()


# Validate that the split monitor credential is internally consistent.
def validate_pair(monitor_path: pathlib.Path, application_path: pathlib.Path) -> None:
    # Derive the expected digest from the raw monitor-only token.
    calculated = expected_digest(monitor_path)
    # Read the application-only configured digest.
    configured = read_assignment(application_path, DIGEST_ENV)
    # Require the application's canonical lowercase digest form.
    if not DIGEST_RE.fullmatch(configured):
        # Reject noncanonical or malformed digest configuration.
        raise ValueError("application digest invalid")
    # Compare digests in constant time even though only the root operator can read both files.
    if not hmac.compare_digest(calculated, configured):
        # Reject mismatched credentials before any production cutover.
        raise ValueError("monitor credential mismatch")


# Render an application environment with exactly one canonical monitor digest assignment.
def render_digest_update(contents: str, digest: str) -> str:
    # Reject an internally generated value if the hashing contract ever regresses.
    if not DIGEST_RE.fullmatch(digest):
        # Keep the writer fail closed.
        raise ValueError("replacement digest invalid")
    # Preserve all unrelated physical lines in their original order.
    lines = contents.splitlines()
    # Track whether the protected setting was already present.
    replaced = False
    # Build the replacement without evaluating any existing shell content.
    updated = []
    # Inspect each original line independently.
    for line in lines:
        # Parse only simple environment assignments.
        match = ASSIGNMENT_RE.fullmatch(line)
        # Preserve unrelated or non-assignment rows byte-for-line.
        if not match or match.group(1) != DIGEST_ENV:
            # Append the untouched line.
            updated.append(line)
            # Continue to the next original row.
            continue
        # Reject duplicate protected assignments instead of silently changing precedence.
        if replaced:
            # Stop without writing any staged file.
            raise ValueError("protected assignment duplicated")
        # Replace the sole protected assignment with the derived canonical digest.
        updated.append(f"{DIGEST_ENV}={digest}")
        # Record the unique replacement.
        replaced = True
    # Append the protected assignment when the application file did not yet contain it.
    if not replaced:
        # Add the canonical assignment after all existing settings.
        updated.append(f"{DIGEST_ENV}={digest}")
    # Emit fixed newlines and one trailing newline for stable systemd parsing.
    return "\n".join(updated) + "\n"


# Atomically repair only the application digest while preserving file metadata.
def repair_digest(monitor_path: pathlib.Path, application_path: pathlib.Path) -> None:
    # Reject symlink destinations so repair cannot be redirected outside the approved file.
    if application_path.is_symlink():
        # Fail before reading or writing the redirect target.
        raise ValueError("application environment must not be a symlink")
    # Read the existing application configuration before staging any replacement.
    contents = application_path.read_text(encoding="utf-8")
    # Read metadata needed to preserve least-privilege ownership and permissions.
    metadata = application_path.stat()
    # Derive the replacement digest from the separate root-managed monitor file.
    digest = expected_digest(monitor_path)
    # Render a replacement that changes only the protected assignment.
    replacement = render_digest_update(contents, digest)
    # Create the staged file beside the destination so os.replace remains atomic.
    descriptor, staging_name = tempfile.mkstemp(prefix=f".{application_path.name}.monitor-", dir=application_path.parent)
    # Wrap staging so every failure removes incomplete bytes.
    try:
        # Open the exclusive descriptor with fixed UTF-8 newlines.
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as staging:
            # Write the complete replacement before metadata or rename operations.
            staging.write(replacement)
            # Flush Python's buffered bytes to the operating system.
            staging.flush()
            # Synchronize the staged bytes before atomic replacement.
            os.fsync(staging.fileno())
        # Preserve the destination's exact permission bits.
        os.chmod(staging_name, stat.S_IMODE(metadata.st_mode))
        # Preserve root ownership on production systems that support chown.
        if hasattr(os, "chown") and os.name != "nt":
            # Apply the original numeric owner and group before replacement.
            os.chown(staging_name, metadata.st_uid, metadata.st_gid)
        # Atomically replace the application environment after all validation succeeds.
        os.replace(staging_name, application_path)
    # Remove a staged file after any failed write, metadata operation, or replacement.
    except Exception:
        # Delete only the exact temporary path created by mkstemp when it still exists.
        if os.path.exists(staging_name):
            # Keep failed partial configuration out of the root-managed directory.
            os.unlink(staging_name)
        # Preserve the original bounded exception category for the command boundary.
        raise
    # Revalidate the installed pair so successful repair cannot leave an inconsistent file.
    validate_pair(monitor_path, application_path)


# Run secret-safe check or explicit repair mode.
def main(argv=None) -> int:
    # Describe the split monitor credential gate.
    parser = argparse.ArgumentParser(description="Validate or repair the root-managed monitor bearer/digest pairing.")
    # Select read-only validation or explicit digest repair.
    parser.add_argument("mode", choices=("check", "repair-digest"), help="Read-only check or explicit application-digest repair")
    # Require the monitor-only environment file containing the raw bearer.
    parser.add_argument("--monitor-env", type=pathlib.Path, required=True, help="Root-managed monitor EnvironmentFile")
    # Require the application environment file containing only the token digest.
    parser.add_argument("--application-env", type=pathlib.Path, required=True, help="Root-managed application EnvironmentFile")
    # Parse operator-supplied paths and mode.
    args = parser.parse_args(argv)
    # Convert every file, format, metadata, and mismatch failure into one secret-safe result.
    try:
        # Perform explicit repair only when the owner selected that mode.
        if args.mode == "repair-digest":
            # Update the digest atomically from the separate bearer file.
            repair_digest(args.monitor_env, args.application_env)
        # Keep deployment workflow use read-only.
        else:
            # Validate the installed pair before cutover.
            validate_pair(args.monitor_env, args.application_env)
    # Bound all expected parsing, filesystem, and replacement failures.
    except (OSError, ValueError):
        # Never print paths, raw authorization, token bytes, or either digest.
        print("monitor configuration invalid: bearer/digest validation failed", file=sys.stderr)
        # Fail closed so deployment cannot switch releases with a broken health credential.
        return 1
    # Report only the completed mode.
    print("monitor configuration repaired" if args.mode == "repair-digest" else "monitor configuration valid")
    # Report successful validation or repair.
    return 0


# Execute the command-line entrypoint when invoked directly.
if __name__ == "__main__":
    # Propagate the fail-closed process status.
    raise SystemExit(main())
