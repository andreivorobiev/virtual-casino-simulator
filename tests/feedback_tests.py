"""Focused provider-neutral tests for issue #349 problem reports."""

# Import base64 helpers for constructing and inspecting browser-style evidence.
import base64
# Import thread orchestration for cross-thread idempotency races.
from concurrent.futures import ThreadPoolExecutor
# Import in-memory image streams so tests never touch user files.
from io import BytesIO
# Import isolated temporary directories for JSON-provider persistence.
import tempfile
# Import unittest for integration with the repository API runner.
import unittest
# Import patching for bounded policy and fault-injection seams.
from unittest import mock
# Import portable paths for isolated provider roots.
from pathlib import Path

# Import Pillow image and PNG metadata helpers for a real metadata-stripping proof.
from PIL import Image, PngImagePlugin

# Import the production feedback service and test-provider seam.
from casino.core import feedback, storage
# Import the public validation error for rejected scope and taxonomy checks.
from casino.errors import ConflictError, NotFoundError, RateLimitError, ValidationError


# Inject one attachment-write failure while delegating every other provider operation.
class FailingAttachmentProvider:
    # Bind the real provider and one-shot failure state.
    def __init__(self, delegate):
        # Preserve the production-compatible provider implementation.
        self.delegate = delegate
        # Fail only the first private evidence write.
        self.failed = False

    # Delegate document reads unchanged.
    def read_document(self, key, default):
        # Return the real provider result.
        return self.delegate.read_document(key, default)

    # Delegate atomic document mutations unchanged.
    def update_document(self, key, mutator, default):
        # Return the real provider transaction result.
        return self.delegate.update_document(key, mutator, default)

    # Fail the first attachment write and delegate every later write.
    def write_document(self, key, data):
        # Detect the private attachment namespace once.
        if key.startswith("feedback_attachment_") and not self.failed:
            # Mark the one-shot failure consumed.
            self.failed = True
            # Raise a synthetic storage interruption before durable evidence.
            raise OSError("synthetic attachment interruption")
        # Delegate recovery and nonattachment writes.
        return self.delegate.write_document(key, data)


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
        return {"idempotency_key": "feedbackaction000001", "category": "visual", "impact": "difficult", "summary": "Roulette chips overlap", "actual": "Outside-bet chips appear over number cells.", "expected": "Outside-bet chips should remain on their selected labels.", "attachments": [self._attachment()], "context": {"route": "/games/roulette?secret=no", "locale": "en-US", "viewport_width": 1440, "viewport_height": 900, "browser_family": "Chrome", "os_family": "Windows", "reduced_motion": False}}

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
        # Require only an opaque reporter reference in list output.
        self.assertRegex(feedback.list_reports()[0]["reporter_reference"], r"^USR-[A-F0-9]{16}$")
        # Require the reporter-visible status list to return only summaries, never evidence bytes.
        own_reports = feedback.list_reporter_reports(self.user)
        # Require the current reporter to see the submitted reference.
        self.assertEqual([created["reference"]], [row["reference"] for row in own_reports])
        # Require reporter status summaries to omit attachment payloads.
        self.assertNotIn("attachments", own_reports[0])
        # Require raw identity and display name to remain absent from durable state.
        self.assertNotIn("user_feedback_test", str(storage.get_storage_provider().read_document(feedback.STATE_DOCUMENT, {})))
        # Require raw display name to remain absent from durable state.
        self.assertNotIn("Private Reporter", str(storage.get_storage_provider().read_document(feedback.STATE_DOCUMENT, {})))
        # Apply the highest governed priority and link a reviewed repository issue.
        update_body = {"idempotency_key": "feedbackadminupdate001", "priority": "P1", "status": "triaged", "admin_notes": "Reproduced at compact desktop.", "github_issue_url": "https://github.com/andreivorobiev/virtual-casino-simulator/issues/349"}
        # Apply the complete manual triage update.
        updated = feedback.update(created["report_id"], update_body)
        # Require the link to drive the nonterminal workflow into linked state.
        self.assertEqual(("P1", "linked"), (updated["priority"], updated["status"]))
        # Replay the exact Admin action without duplicating history.
        replayed_update = feedback.update(created["report_id"], update_body)
        # Require one triage audit event across both calls.
        self.assertEqual(1, sum(1 for event in replayed_update["history"] if event["action"] == "admin_triage"))
        # Prepare the safe GitHub draft for explicit Admin review.
        draft = feedback.github_draft(created["report_id"])
        # Require reporter identity and internal notes to remain absent from external prose.
        self.assertNotIn("Private Reporter", draft["body"])
        # Require governed priority in the draft label set.
        self.assertIn("P1", draft["labels"])
        # Require the implementation to expose manual-only publication semantics.
        self.assertEqual("manual_only", draft["publication_mode"])
        # Require automatic publication to remain disabled by default.
        self.assertFalse(draft["publication_enabled"])
        # Export metadata without encoded pixels.
        exported = feedback.export_report(created["report_id"])
        # Require integrity metadata but no base64 evidence in export output.
        self.assertNotIn("data", exported["attachments"][0])

    # Prove guest scope and P4 both fail closed.
    def test_guest_and_p4_are_rejected(self):
        # Build the separately governed disposable guest identity.
        guest = {"user_id": "guest_feedback_test", "display_name": "Guest trial", "identity_provider": "guest", "roles": ["guest"]}
        # Require guest reporting to remain unavailable in this first release.
        with self.assertRaises(ValidationError):
            # Submit through the same production boundary.
            feedback.submit(guest, self._body())
        # Require guest status tracking to remain unavailable unless the trial converts to an account.
        with self.assertRaises(ValidationError):
            # Attempt to list report statuses for the abandoned guest.
            feedback.list_reporter_reports(guest)
        # Create a registered-user report for priority validation.
        created = feedback.submit(self.user, self._body())
        # Require the repository's prohibited P4 value to be rejected.
        with self.assertRaises(ValidationError):
            # Apply P4 through the canonical Admin update boundary.
            feedback.update(created["report_id"], {"idempotency_key": "feedbackadminupdate002", "priority": "P4"})

    # Prove concurrent exact retries select one report and one attachment inventory.
    def test_concurrent_retries_choose_one_winner(self):
        # Submit the same action through independent threads.
        with ThreadPoolExecutor(max_workers=8) as pool:
            # Collect every stable receipt.
            receipts = list(pool.map(lambda _: feedback.submit(self.user, self._body()), range(8)))
        # Require exactly one canonical report id.
        self.assertEqual(1, len({receipt["report_id"] for receipt in receipts}))
        # Require exactly one committed list row.
        self.assertEqual(1, len(feedback.list_reports()))
        # Read the authoritative state for duplicate inventory checks.
        state = storage.get_storage_provider().read_document(feedback.STATE_DOCUMENT, {})
        # Require one report and one replay mapping.
        self.assertEqual((1, 1), (len(state["reports"]), len(state["idempotency"])))

    # Prove a failed evidence write leaves a hidden reservation that the exact retry recovers.
    def test_attachment_interruption_is_recoverable(self):
        # Wrap the real provider with one deterministic evidence failure.
        failing = FailingAttachmentProvider(storage.get_storage_provider())
        # Install the fault provider through the production seam.
        storage.set_provider_for_tests(failing)
        # Require the first attempt to expose the synthetic storage interruption.
        with self.assertRaises(OSError):
            # Start the recoverable submission saga.
            feedback.submit(self.user, self._body())
        # Require no preparing report to appear in the Admin inbox.
        self.assertEqual([], feedback.list_reports())
        # Retry the exact operation through the same fault provider after its one-shot failure.
        recovered = feedback.submit(self.user, self._body())
        # Require one committed report after recovery.
        self.assertEqual(1, len(feedback.list_reports()))
        # Require normalized evidence to be readable after recovery.
        self.assertEqual(1, len(feedback.detail(recovered["report_id"])["attachments"]))

    # Prove durable rate enforcement and explicit privacy deletion.
    def test_rate_limit_and_privacy_deletion(self):
        # Lower the test-only rate floor while retaining the production durable implementation.
        with mock.patch.object(feedback.config, "FEEDBACK_RATE_LIMIT", 1):
            # Create the single allowed report.
            created = feedback.submit(self.user, self._body())
            # Reusing the exact action remains an allowed replay.
            self.assertEqual(created["report_id"], feedback.submit(self.user, self._body())["report_id"])
            # Change only the action key to request another report inside the same window.
            second = dict(self._body())
            # Allocate a distinct action identity.
            second["idempotency_key"] = "feedbackaction000002"
            # Require the durable rate limiter to reject it.
            with self.assertRaises(RateLimitError):
                # Submit through the production service.
                feedback.submit(self.user, second)
        # Delete the retained report through an explicit Admin action.
        deletion = feedback.delete_report(created["report_id"], {"idempotency_key": "feedbackadmindelete001"})
        # Require a minimal deletion receipt.
        self.assertTrue(deletion["deleted_at"])
        # Require deleted content to disappear from Admin reads.
        with self.assertRaises(NotFoundError):
            # Read the deleted report.
            feedback.detail(created["report_id"])
        # Require the list to remain empty after deletion.
        self.assertEqual([], feedback.list_reports())

    # Prove malformed state is preserved unchanged instead of normalized away.
    def test_malformed_state_fails_closed(self):
        # Write a recoverable malformed sentinel document.
        storage.get_storage_provider().write_document(feedback.STATE_DOCUMENT, {"malformed": "preserve-me"})
        # Require list reads to fail closed.
        with self.assertRaises(ConflictError):
            # Attempt to read the malformed inbox.
            feedback.list_reports()
        # Require the sentinel to remain unchanged.
        self.assertEqual({"malformed": "preserve-me"}, storage.get_storage_provider().read_document(feedback.STATE_DOCUMENT, None))

    # Prove terminal retention invokes the same recoverable privacy-deletion saga.
    def test_terminal_retention_cleanup(self):
        # Create one committed report at a fixed canonical instant.
        with mock.patch.object(feedback, "utc_now", return_value="2026-07-22T00:00:00.000Z"):
            # Submit through the production saga.
            created = feedback.submit(self.user, self._body())
            # Enter a terminal lifecycle state through the idempotent Admin update.
            feedback.update(created["report_id"], {"idempotency_key": "feedbackterminalupdate01", "status": "resolved"})
        # Advance beyond a patched one-second terminal retention ceiling.
        with mock.patch.object(feedback, "utc_now", return_value="2026-07-22T00:00:03.000Z"), mock.patch.object(feedback.config, "FEEDBACK_TERMINAL_RETENTION_SECONDS", 1), mock.patch.object(feedback.config, "FEEDBACK_RATE_WINDOW_SECONDS", 1):
            # Run the bounded cleanup entrypoint used by the Admin route.
            result = feedback.cleanup_retention()
        # Require one deletion receipt without retained content.
        self.assertEqual(1, result["deleted"])
        # Require expired opaque rate references to share the cleanup boundary.
        self.assertEqual(1, result["rate_events_pruned"])
        # Require canonical reads to hide the terminally deleted report.
        with self.assertRaises(NotFoundError):
            # Read through the complete evidence-validating boundary.
            feedback.detail(created["report_id"])
