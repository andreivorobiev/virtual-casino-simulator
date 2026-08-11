# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Durable provider operational-switch tests for OAUTH-012 and TEST-167."""

# Import temporary directories for isolated provider documents.
import tempfile
# Import unittest and patching for the configured provider seam.
import unittest
# Import paths for the isolated JSON provider.
from pathlib import Path
# Import mock patching without changing global storage configuration.
from unittest.mock import patch

# Import the owner-controlled switch module under test.
from casino.core import oauth_controls
# Import the provider implementation used by ordinary JSON runtime tests.
from casino.core.storage import JsonStorageProvider
# Import stable stale-write and validation failures.
from casino.errors import ConflictError, ValidationError


# Prove default-off, optimistic, audited, and fail-closed switch behavior.
class OAuthOperationalControlsTests(unittest.TestCase):
    # Create one isolated provider before each test.
    def setUp(self):
        # Retain a task-owned temporary root until cleanup.
        self.temporary = tempfile.TemporaryDirectory()
        # Build the JSON provider beneath the isolated root.
        self.provider = JsonStorageProvider(Path(self.temporary.name) / "data")
        # Create only provider-owned directories inside the temporary root.
        self.provider.ensure_ready()
        # Redirect the module's configured-provider read through the isolated instance.
        self.provider_patch = patch("casino.core.oauth_controls.get_storage_provider", return_value=self.provider)
        # Activate the isolated provider seam.
        self.provider_patch.start()

    # Remove only test-owned state after each case.
    def tearDown(self):
        # Restore the production provider resolver.
        self.provider_patch.stop()
        # Delete the task-owned temporary root.
        self.temporary.cleanup()

    # Prove absent state defaults both providers off and unknown providers fail closed.
    def test_defaults_are_disabled(self):
        # Read one strict default document.
        state = oauth_controls.current()
        # Require the exact default-off switch and audit shape.
        self.assertEqual(state, {"schema_version": 1, "revision": 0, "providers": {"google": False, "facebook": False}, "audit": []})
        # Require every reviewed and unknown provider to remain unavailable initially.
        self.assertFalse(oauth_controls.enabled("google"))
        # Reject an unreviewed provider by secure default.
        self.assertFalse(oauth_controls.enabled("unknown"))

    # Prove one owner transition is atomic, audited, and revision-bound.
    def test_update_is_audited_and_stale_writes_fail(self):
        # Preview one bounded provider enablement.
        preview = oauth_controls.propose({"google": True})
        # Require exact changed-provider and no lockout impact.
        self.assertEqual(preview["impact"], {"providers_changed": ["google"], "existing_login_disabled": []})
        # Commit the exact preview revision with bounded synthetic owner evidence.
        result = oauth_controls.update({"google": True}, actor_id="owner-synthetic", reason="Synthetic readiness acceptance", expected_revision=preview["revision"])
        # Require the switch, revision, and immutable audit transition to commit together.
        self.assertEqual((result["revision"], result["providers"]), (1, {"google": True, "facebook": False}))
        # Require the read path to observe the exact committed gate.
        self.assertTrue(oauth_controls.enabled("google"))
        # Reject the stale original revision without another row.
        with self.assertRaises(ConflictError):
            # Attempt no second mutation from a consumed preview.
            oauth_controls.update({"facebook": True}, actor_id="owner-synthetic", reason="Stale synthetic change", expected_revision=0)
        # Require one and only one immutable audit row after the rejected write.
        self.assertEqual(len(oauth_controls.current()["audit"]), 1)

    # Prove malformed provider changes never reach storage.
    def test_invalid_changes_fail_closed(self):
        # Exercise unknown providers, truthy aliases, and empty changes.
        for changes in ({"github": True}, {"google": "true"}, {}):
            # Label only the fixed malformed shape.
            with self.subTest(changes=changes):
                # Reject the proposal before durable mutation.
                with self.assertRaises(ValidationError):
                    # Preview no unreviewed control.
                    oauth_controls.propose(changes)
        # Preserve the absent-document default after every rejection.
        self.assertEqual(oauth_controls.current()["revision"], 0)


# Run focused tests directly when invoked outside the repository harness.
if __name__ == "__main__":
    # Use unittest's standard runner without custom listeners or state.
    unittest.main()
