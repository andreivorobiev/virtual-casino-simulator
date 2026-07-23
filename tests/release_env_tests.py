"""Focused deployment build-provenance fragment tests. (#287, TOOL-007)"""

# Import output redirection so the tool's operator messages never enter suite output.
import contextlib
# Import an in-memory stream for captured operator messages.
import io
# Import JSON writing for the release manifest fixtures.
import json
# Import filesystem paths for isolated fixture handling.
import pathlib
# Import isolated temporary directories so no repository file is ever written.
import tempfile
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Import the deployment provenance tool under test.
from scripts import write_release_env

# Use one fixed valid commit so every assertion is deterministic.
VALID_COMMIT = "0123456789abcdef0123456789abcdef01234567"


# Verify the deployment fragment pins an exact commit and fails closed otherwise.
class ReleaseEnvFragmentTests(unittest.TestCase):
    # Create one isolated working directory for each test.
    def setUp(self) -> None:
        # Open a temporary directory that is removed when the test ends.
        self._directory = tempfile.TemporaryDirectory()
        # Retain the resolved fixture root.
        self.root = pathlib.Path(self._directory.name)
        # Point at the destination fragment the service unit would source.
        self.destination = self.root / "release.env"

    # Remove the isolated fixture directory after each test.
    def tearDown(self) -> None:
        # Release the temporary directory and its contents.
        self._directory.cleanup()

    # Invoke the deployment tool while capturing its bounded operator messages.
    def _run(self, manifest) -> int:
        # Discard both streams so a passing suite prints nothing.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            # Return the deployment-step exit status.
            return write_release_env.main(["--manifest", str(manifest), "--destination", str(self.destination)])

    # Write one release manifest fixture and return its path.
    def _manifest(self, source) -> pathlib.Path:
        # Point at the manifest fixture inside the isolated directory.
        path = self.root / "release-manifest.json"
        # Persist only the source block the tool is allowed to read.
        path.write_text(json.dumps({"app_version": "9.3.0", "source": source}), encoding="utf-8")
        # Return the fixture path.
        return path

    # Require a valid manifest to produce exactly one pinned assignment.
    def test_valid_manifest_pins_the_exact_commit(self) -> None:
        # Build a manifest carrying a full lowercase commit.
        manifest = self._manifest({"commit_sha": VALID_COMMIT, "release_tag": "v9.3.0"})
        # Require the deployment step to succeed.
        self.assertEqual(self._run(manifest), 0)
        # Read the generated fragment.
        written = self.destination.read_text(encoding="utf-8")
        # Require the exact pinned assignment.
        self.assertIn(f"CASINO_BUILD_SHA={VALID_COMMIT}\n", written)
        # Require exactly one assignment so the fragment can never carry additional configuration.
        self.assertEqual([line for line in written.splitlines() if line and not line.startswith("#")], [f"CASINO_BUILD_SHA={VALID_COMMIT}"])

    # Require the generated value to satisfy the runtime sanitizer that publishes it.
    def test_generated_value_survives_the_operations_sanitizer(self) -> None:
        # Import the Operations sanitizer that guards every published provenance value.
        from casino.operations.probes import sanitize_build_sha
        # Build and write a valid fragment.
        manifest = self._manifest({"commit_sha": VALID_COMMIT, "release_tag": "v9.3.0"})
        self._run(manifest)
        # Extract the written value the service unit would export.
        value = self.destination.read_text(encoding="utf-8").rsplit("=", 1)[1].strip()
        # Require the sanitizer to accept it unchanged so the deployment actually publishes provenance.
        self.assertEqual(sanitize_build_sha(value), VALID_COMMIT)

    # Require every unpinnable manifest to fail the deployment step without writing a fragment.
    def test_unpinnable_manifests_fail_closed(self) -> None:
        # Enumerate short, uppercase, non-hexadecimal, absent, and malformed source blocks.
        rejected = [{"commit_sha": "0123456"}, {"commit_sha": VALID_COMMIT.upper()}, {"commit_sha": "z" * 40}, {"release_tag": "v9.3.0"}, {"commit_sha": None}]
        # Check every rejected manifest shape.
        for source in rejected:
            # Isolate each case so a prior failure cannot mask the next.
            with self.subTest(source=source):
                # Build the unpinnable manifest fixture.
                manifest = self._manifest(source)
                # Require a non-zero deployment exit status.
                self.assertEqual(self._run(manifest), 1)
                # Require no fragment to have been written for an unpinnable release.
                self.assertFalse(self.destination.exists())

    # Require an unreadable manifest to fail closed rather than install stale provenance.
    def test_missing_manifest_leaves_previous_provenance_untouched(self) -> None:
        # Seed a previously generated fragment from an earlier deployment.
        self.destination.write_text("CASINO_BUILD_SHA=" + ("a" * 40) + "\n", encoding="utf-8")
        # Require the step to fail when the manifest is absent.
        self.assertEqual(self._run(self.root / "absent.json"), 1)
        # Require the earlier fragment to remain byte-identical rather than being truncated.
        self.assertEqual(self.destination.read_text(encoding="utf-8"), "CASINO_BUILD_SHA=" + ("a" * 40) + "\n")

    # Require a redeployment to replace the previous commit rather than append to it.
    def test_redeployment_replaces_the_previous_commit(self) -> None:
        # Seed a fragment from an earlier release.
        self.destination.write_text("CASINO_BUILD_SHA=" + ("a" * 40) + "\n", encoding="utf-8")
        # Write the fragment for the new release.
        manifest = self._manifest({"commit_sha": VALID_COMMIT, "release_tag": "v9.3.1"})
        self._run(manifest)
        # Read the replaced fragment.
        written = self.destination.read_text(encoding="utf-8")
        # Require the superseded commit to be gone so systemd cannot export a stale value.
        self.assertNotIn("a" * 40, written)
        # Require exactly one assignment to remain.
        self.assertEqual([line for line in written.splitlines() if line and not line.startswith("#")], [f"CASINO_BUILD_SHA={VALID_COMMIT}"])

    # Require the tracked service unit to source the generated fragment after the secret environment file.
    def test_service_unit_sources_the_generated_fragment_last(self) -> None:
        # Read the tracked production unit template.
        unit = (pathlib.Path(__file__).resolve().parents[1] / "deploy" / "systemd" / "casino.service").read_text(encoding="utf-8")
        # Collect the ordered environment-file directives.
        directives = [line.strip() for line in unit.splitlines() if line.strip().startswith("EnvironmentFile=")]
        # Require the operator secret file first and the generated provenance fragment last.
        self.assertEqual(directives, ["EnvironmentFile=/etc/casino/casino.env", "EnvironmentFile=-/etc/casino/release.env"])
