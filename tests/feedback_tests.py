"""Focused provider-neutral tests for issue #349 problem reports."""

# Import base64 helpers for constructing and inspecting browser-style evidence.
import base64
# Import in-memory image streams so tests never touch user files.
from io import BytesIO
# Import isolated temporary directories for JSON-provider persistence.
import tempfile
# Import unittest for integration with the repository API runner.
import unittest
# Import portable paths for isolated provider roots.
from pathlib import Path

# Import Pillow image and PNG metadata helpers for a real metadata-stripping proof.
from PIL import Image, PngImagePlugin

# Import the production feedback service and test-provider seam.
from casino.core import feedback, storage
# Import the public validation error for rejected scope and taxonomy checks.
from casino.errors import ValidationError


# Exercise submission, evidence sanitation, idempotency, and Admin triage as one service boundary.
class FeedbackServiceTests(unittest.TestCase):
    # Install one fresh provider before every test.
    def setUp(self):
        # Create a temporary root retained for the duration of the test.
        self.temporary = tempfile.TemporaryDirectory()
        # Point all production feedback calls at the isolated JSON provider.
        storage.set_provider_for_tests(storage.JsonStorageProvider(Path(self.temporary.name) / "data"))
        # Define a registered player identity that contains internal reporter details.
        self.user = {"user_id": "user_feedback_test", "display_name": "Private Reporter", "identity_provider": "local", "roles": ["player"]}

    # Restore global provider selection and remove isolated data after every test.
    def tearDown(self):
        # Release the injected provider before another suite runs.
        storage.set_provider_for_tests(None)
        # Remove the temporary directory through its owned cleanup API.
        self.temporary.cleanup()

    # Build a small valid PNG carrying metadata that must not survive normalization.
    def _attachment(self) -> dict:
        # Allocate a deterministic image with visible color variation.
        image = Image.new("RGB", (80, 50), (18, 90, 54))
        # Add a private marker to a PNG text chunk.
        metadata = PngImagePlugin.PngInfo()
        # Store the marker only in source metadata, never visible pixels.
        metadata.add_text("private_note", "must-not-survive")
        # Encode the source image to memory.
        output = BytesIO()
        # Save a genuine PNG with the private metadata chunk.
        image.save(output, format="PNG", pnginfo=metadata)
        # Return the same data-URL shape accepted from the browser.
        return {"data": "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")}

    # Build the smallest complete valid submission packet.
    def _body(self) -> dict:
        # Return bounded prose, evidence, and privacy-reduced context.
        return {"idempotency_key": "feedbackaction000001", "category": "visual", "summary": "Roulette chips overlap", "actual": "Outside-bet chips appear over number cells.", "expected": "Outside-bet chips should remain on their selected labels.", "attachments": [self._attachment()], "context": {"route": "/games/roulette?secret=no", "locale": "en-US", "viewport_width": 1440, "viewport_height": 900, "browser_family": "Chrome", "os_family": "Windows", "reduced_motion": False}}

    # Prove a complete retry-safe lifecycle without publishing reporter identity externally.
    def test_submission_evidence_idempotency_and_triage(self):
        # Submit the first canonical report.
        created = feedback.submit(self.user, self._body())
        # Require a human-searchable confirmation reference and default governed priority.
        self.assertTrue(created["reference"].startswith("RPT-"))
        # Repeat the exact action identity to prove no duplicate report is created.
        replay = feedback.submit(self.user, self._body())
        # Require the stable canonical identifier on retry.
        self.assertEqual(created["report_id"], replay["report_id"])
        # Require the service to distinguish a replay for diagnostics.
        self.assertTrue(replay["replayed"])
        # Read canonical Admin detail.
        report = feedback.detail(created["report_id"])
        # Require query-string removal from retained route context.
        self.assertEqual("/games/roulette", report["route"])
        # Require the low-cardinality browser and operating-system families to survive unchanged.
        self.assertEqual(("Chrome", "Windows"), (report["context"]["browser_family"], report["context"]["os_family"]))
        # Require a server-normalized JPEG regardless of source format.
        self.assertEqual("image/jpeg", report["attachments"][0]["media_type"])
        # Require source PNG metadata to be absent from normalized evidence bytes.
        self.assertNotIn(b"must-not-survive", base64.b64decode(report["attachments"][0]["data"]))
        # Require list summaries to exclude encoded evidence and prose detail.
        self.assertNotIn("attachments", feedback.list_reports()[0])
        # Apply the highest governed priority and link a reviewed repository issue.
        updated = feedback.update(created["report_id"], {"priority": "P1", "status": "triaged", "admin_notes": "Reproduced at compact desktop.", "github_issue_url": "https://github.com/andreivorobiev/virtual-casino-simulator/issues/349"})
        # Require the link to drive the nonterminal workflow into linked state.
        self.assertEqual(("P1", "linked"), (updated["priority"], updated["status"]))
        # Prepare the safe GitHub draft for explicit Admin review.
        draft = feedback.github_draft(created["report_id"])
        # Require reporter identity and internal notes to remain absent from external prose.
        self.assertNotIn("Private Reporter", draft["body"])
        # Require governed priority in the draft label set.
        self.assertIn("P1", draft["labels"])

    # Prove guest scope and P4 both fail closed.
    def test_guest_and_p4_are_rejected(self):
        # Build the separately governed disposable guest identity.
        guest = {"user_id": "guest_feedback_test", "display_name": "Guest trial", "identity_provider": "guest", "roles": ["guest"]}
        # Require guest reporting to remain unavailable in this first release.
        with self.assertRaises(ValidationError):
            # Submit through the same production boundary.
            feedback.submit(guest, self._body())
        # Create a registered-user report for priority validation.
        created = feedback.submit(self.user, self._body())
        # Require the repository's prohibited P4 value to be rejected.
        with self.assertRaises(ValidationError):
            # Apply P4 through the canonical Admin update boundary.
            feedback.update(created["report_id"], {"priority": "P4"})
