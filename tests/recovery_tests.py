"""Focused secret-safe recovery evidence tests for TEST-049."""

# Import copies so tamper tests never mutate shared fixture objects.
import copy
# Import UTC times for deterministic freshness evidence.
from datetime import datetime, timezone
# Import unittest for the repository's dependency-free focused test style.
import unittest
# Import in-memory binary streams for bounded encryption tests.
import io
# Import binary framing helpers to mutate one exact authenticated chunk.
import struct
# Import temporary directories for encrypted-staging-only orchestration tests.
import tempfile
# Import portable paths for redacted process configuration fixtures.
from pathlib import Path
# Import mocks for deterministic no-shell child process tests.
from unittest import mock
# Import threading events for controlled watchdog timeout evidence.
import threading

# Import only the repository-side recovery evidence contract.
from casino.core import recovery
# Import the immutable #204 schema contract for exact recovery context fixtures.
from casino.core.mysql_migrations import schema_contract
# Import the packaged CLI loader for least-privilege child environment tests.
from scripts import recovery as recovery_cli

# Use independent deterministic synthetic keys that never leave this test process.
ENCRYPTION_KEY = b"e" * 32
# Use a distinct HMAC key to prove role-separation enforcement.
EVIDENCE_KEY = b"h" * 32
# Use an independent destination acknowledgement authority.
DESTINATION_KEY = b"d" * 32
# Use an independent provider read-only evidence authority.
PROVIDER_KEY = b"p" * 32
# Use an independent clean-target authorization and result authority.
RESTORE_KEY = b"r" * 32
# Fix the decision time so freshness tests remain deterministic.
NOW = datetime(2026, 7, 16, 20, 0, tzinfo=timezone.utc)
# Bind every fixture to the exact packaged #204 migration chain.
MIGRATION_CHAIN = schema_contract()["migration_chain_sha256"]


# Construct all pairwise-independent synthetic key roles.
def recovery_keys():
    # Return one fully validated redacted key record.
    return recovery.RecoveryKeys(ENCRYPTION_KEY, EVIDENCE_KEY, DESTINATION_KEY, PROVIDER_KEY, RESTORE_KEY)


# Build one sanitized provider evidence record with no provider identifiers.
def provider_record():
    # Return only completion, observation, and cost-inclusion semantics.
    return {
        # Identify the reviewed provider evidence contract.
        "schema": recovery.PROVIDER_EVIDENCE_SCHEMA,
        # Record a completed backup state.
        "completed": True,
        # Record a current backup completion time.
        "completed_at": "2026-07-16T19:30:00+00:00",
        # Record a later read-only verification time.
        "verified_at": "2026-07-16T19:40:00+00:00",
        # Record explicit inclusion in the already approved VM price.
        "cost_included": True,
    }


# Build one sanitized encrypted recovery manifest with opaque bindings only.
def manifest_record():
    # Return exact artifact, release, schema, target, and acknowledgement bindings.
    return {
        # Identify the reviewed encrypted recovery manifest contract.
        "schema": recovery.RECOVERY_MANIFEST_SCHEMA,
        # Bind exact synthetic encrypted bytes.
        "encrypted_artifact_sha256": "a" * 64,
        # Bind exact ciphertext bytes with an independent keyed digest.
        "encrypted_artifact_hmac_sha256": "e" * 64,
        # Bind exact encrypted length.
        "encrypted_size": 512,
        # Bind the authenticated terminal's exact logical length.
        "logical_plaintext_size": 256,
        # Bind the authenticated terminal's exact logical digest.
        "logical_plaintext_sha256": "2" * 64,
        # Bind the only reviewed streaming encryption format.
        "encryption_schema": recovery.ENCRYPTED_STREAM_SCHEMA,
        # Bind exact authenticated header bytes.
        "encryption_header_sha256": "f" * 64,
        # Bind the complete signed destination acknowledgement.
        "destination_ack_sha256": "1" * 64,
        # Bind a full synthetic immutable release SHA.
        "release_sha": "b" * 40,
        # Bind the canonical semantic application version.
        "app_version": "9.2.0",
        # Bind the independent MySQL schema version from #204.
        "mysql_schema_version": 2,
        # Bind the checksum-ordered migration chain.
        "migration_chain_sha256": MIGRATION_CHAIN,
        # Bind the source without exposing a target identifier.
        "source_target_hmac_sha256": "d" * 64,
        # Record encrypted backup completion.
        "completed_at": "2026-07-16T19:30:00+00:00",
        # Record acknowledgement of the exact encrypted bytes.
        "destination_acknowledged_at": "2026-07-16T19:35:00+00:00",
        # Retain the acknowledged object beyond the restore decision.
        "retention_until": "2026-07-23T19:35:00+00:00",
    }


# Build one signed durable off-instance acknowledgement for exact fixture bytes.
def signed_destination_ack():
    # Sign only durable completion, exact artifact, and retention semantics.
    return recovery.sign_evidence({
        # Identify the reviewed destination acknowledgement contract.
        "schema": "casino-off-instance-destination-ack-v1",
        # Require completed transfer.
        "completed": True,
        # Require durable destination state.
        "durable": True,
        # Require a separate failure domain rather than local staging.
        "off_instance": True,
        # Bind exact encrypted bytes.
        "encrypted_artifact_sha256": "a" * 64,
        # Bind exact encrypted length.
        "encrypted_size": 512,
        # Record acknowledgement after logical backup completion.
        "acknowledged_at": "2026-07-16T19:35:00+00:00",
        # Record active bounded retention.
        "retention_until": "2026-07-23T19:35:00+00:00",
    }, DESTINATION_KEY)


# Build a manifest paired to the exact signed destination acknowledgement.
def signed_manifest_pair():
    # Create the destination-owned signed acknowledgement.
    acknowledgement_record = signed_destination_ack()
    # Validate it at the deterministic decision time.
    acknowledgement = recovery.validate_destination_acknowledgement(acknowledgement_record, DESTINATION_KEY, "a" * 64, 512, NOW)
    # Build the source-owned manifest fields.
    manifest = manifest_record()
    # Bind the complete destination acknowledgement digest.
    manifest["destination_ack_sha256"] = acknowledgement.evidence_sha256
    # Return independently signed records.
    return recovery.sign_evidence(manifest, EVIDENCE_KEY), acknowledgement_record


# Build a complete real encrypted artifact plus paired signed recovery evidence.
def encrypted_recovery_bundle(plaintext=None):
    # Bind only the strict public release/schema/source context.
    context = {"release_sha": "b" * 40, "app_version": "9.2.0", "mysql_schema_version": 2, "migration_chain_sha256": MIGRATION_CHAIN, "source_target_hmac_sha256": "d" * 64}
    # Use representative synthetic persistence rows only.
    plaintext = plaintext or b"synthetic-user\tsynthetic-wallet\tsynthetic-ledger\n"
    # Encrypt into memory so no plaintext file can exist.
    artifact = io.BytesIO()
    # Capture terminal and authenticated-header metadata.
    metadata = recovery.encrypt_stream(io.BytesIO(plaintext), artifact, ENCRYPTION_KEY, context)
    # Compute exact encrypted public and keyed identities.
    artifact_sha256, artifact_hmac_sha256, artifact_size = recovery.encrypted_artifact_identity(artifact, EVIDENCE_KEY)
    # Build destination-owned exact ciphertext acknowledgement.
    acknowledgement = recovery.sign_evidence({
        # Identify the destination contract.
        "schema": "casino-off-instance-destination-ack-v1",
        # Record complete durable off-instance state.
        "completed": True,
        # Require durable object state.
        "durable": True,
        # Require a separate failure domain.
        "off_instance": True,
        # Bind exact encrypted bytes.
        "encrypted_artifact_sha256": artifact_sha256,
        # Bind exact encrypted length.
        "encrypted_size": artifact_size,
        # Record destination acknowledgement after backup completion.
        "acknowledged_at": "2026-07-16T19:35:00+00:00",
        # Retain for the minimum reviewed seven-day window.
        "retention_until": "2026-07-23T19:35:00+00:00",
    }, DESTINATION_KEY)
    # Validate destination evidence to obtain its exact signed digest.
    validated_ack = recovery.validate_destination_acknowledgement(acknowledgement, DESTINATION_KEY, artifact_sha256, artifact_size, NOW)
    # Build the manifest paired to exact destination evidence.
    manifest = recovery.sign_evidence({
        # Identify the recovery manifest contract.
        "schema": recovery.RECOVERY_MANIFEST_SCHEMA,
        # Bind exact ciphertext public checksum.
        "encrypted_artifact_sha256": artifact_sha256,
        # Bind exact ciphertext keyed digest.
        "encrypted_artifact_hmac_sha256": artifact_hmac_sha256,
        # Bind exact ciphertext length.
        "encrypted_size": artifact_size,
        # Bind authenticated terminal logical length.
        "logical_plaintext_size": metadata["plaintext_size"],
        # Bind authenticated terminal logical digest.
        "logical_plaintext_sha256": metadata["plaintext_sha256"],
        # Bind reviewed chunked AEAD format.
        "encryption_schema": metadata["encryption_schema"],
        # Bind exact authenticated header.
        "encryption_header_sha256": metadata["encryption_header_sha256"],
        # Bind exact signed destination acknowledgement.
        "destination_ack_sha256": validated_ack.evidence_sha256,
        # Bind immutable release SHA.
        "release_sha": context["release_sha"],
        # Bind canonical application version.
        "app_version": context["app_version"],
        # Bind #204 schema version.
        "mysql_schema_version": context["mysql_schema_version"],
        # Bind #204 migration chain.
        "migration_chain_sha256": context["migration_chain_sha256"],
        # Bind source target opaquely.
        "source_target_hmac_sha256": context["source_target_hmac_sha256"],
        # Record logical backup completion.
        "completed_at": "2026-07-16T19:30:00+00:00",
        # Copy destination acknowledgement time exactly.
        "destination_acknowledged_at": "2026-07-16T19:35:00+00:00",
        # Copy destination retention exactly.
        "retention_until": "2026-07-23T19:35:00+00:00",
    }, EVIDENCE_KEY)
    # Return only synthetic bytes and signed records.
    return plaintext, artifact.getvalue(), context, manifest, acknowledgement


# Build one independent empty-target authorization.
def signed_restore_authorization():
    # Sign exact empty isolated target semantics.
    return recovery.sign_evidence({
        # Identify the clean-target contract.
        "schema": "casino-clean-restore-authorization-v1",
        # Bind the isolated target opaquely.
        "target_hmac_sha256": "9" * 64,
        # Require explicit clean target.
        "clean_target": True,
        # Require explicit empty target.
        "empty_target": True,
        # Require disposable test target.
        "disposable": True,
        # Reject ambient or live target state.
        "ambient_target": False,
        # Prove zero tables before restore.
        "existing_table_count": 0,
        # Bind exact empty-state observation.
        "empty_state_sha256": "0" * 64,
        # Record target preparation shortly before restore.
        "prepared_at": "2026-07-16T19:50:00+00:00",
        # Expire within the one-hour authorization bound.
        "expires_at": "2026-07-16T20:30:00+00:00",
    }, RESTORE_KEY)


# Retain written bytes even when production orchestration closes child stdin.
class RetainedSink(io.BytesIO):
    # Track close requests without discarding synthetic bytes.
    def close(self):
        # Record the production close boundary.
        self.close_requested = True


# Model one deterministic argv-free restore wrapper process.
class FakeRestoreProcess:
    # Initialize a configurable stdin sink and exit status.
    def __init__(self, sink=None, return_code=0):
        # Expose the binary stdin expected by production code.
        self.stdin = sink or RetainedSink()
        # Store the configured eventual status.
        self.return_code = return_code
        # Track whether process wait completed.
        self.waited = False
        # Track mandatory kill behavior after partial failure.
        self.killed = False

    # Report running until wait or kill completes.
    def poll(self):
        # Return no status while active.
        return self.return_code if self.waited or self.killed else None

    # Complete deterministic process reaping.
    def wait(self, timeout=None):
        # Record successful reap.
        self.waited = True
        # Return configured status without exposing arguments.
        return self.return_code

    # Mark the tracked synthetic child killed.
    def kill(self):
        # Record exact kill behavior.
        self.killed = True
        # Use one nonzero synthetic status after kill.
        self.return_code = -1


# Model one deterministic argv-free logical dump wrapper process.
class FakeDumpProcess:
    # Initialize synthetic logical bytes and eventual exit status.
    def __init__(self, logical_bytes, return_code=0):
        # Expose binary stdout exactly as production encryption expects.
        self.stdout = io.BytesIO(logical_bytes)
        # Store eventual status.
        self.return_code = return_code
        # Track process reaping.
        self.waited = False
        # Track watchdog kill behavior.
        self.killed = False

    # Report running until wait or kill.
    def poll(self):
        # Return no status while active.
        return self.return_code if self.waited or self.killed else None

    # Complete deterministic process reaping.
    def wait(self, timeout=None):
        # Record the reap.
        self.waited = True
        # Return configured status.
        return self.return_code

    # Mark the tracked dump wrapper killed.
    def kill(self):
        # Record kill evidence.
        self.killed = True
        # Use one nonzero synthetic status.
        self.return_code = -1


# Model a destination adapter over synthetic memory only.
class SyntheticDestination:
    # Store exact encrypted bytes under independent acknowledgement authority.
    def __init__(self, artifact, downloaded_at="2026-07-16T20:00:00+00:00"):
        # Retain only synthetic encrypted content.
        self.artifact = artifact
        # Retain one sanitized signed download completion timestamp.
        self.downloaded_at = downloaded_at

    # Download exact encrypted bytes and return a signed receipt.
    def download_artifact(self, target, expected_sha256, expected_size):
        # Stream only encrypted bytes into the provided staging handle.
        target.write(self.artifact)
        # Return independently signed exact download evidence.
        return recovery.sign_evidence({"schema": "casino-off-instance-download-receipt-v1", "completed": True, "durable": True, "off_instance": True, "encrypted_artifact_sha256": expected_sha256, "encrypted_size": expected_size, "downloaded_at": self.downloaded_at}, DESTINATION_KEY)


# Model upload, exact acknowledgement, and manifest commit over synthetic memory.
class SyntheticUploadDestination:
    # Initialize optional acknowledgement failure modes.
    def __init__(self, bad_upload=False, bad_manifest=False):
        # Configure a bad artifact acknowledgement.
        self.bad_upload = bad_upload
        # Configure a bad manifest acknowledgement.
        self.bad_manifest = bad_manifest
        # Retain exact signed artifact acknowledgement for later pairing.
        self.acknowledgement = None
        # Track whether encrypted staging still existed during commit.
        self.staging_present_during_commit = False
        # Retain uploaded encrypted bytes only.
        self.encrypted_bytes = b""
        # Retain the staging path for policy assertions.
        self.staging_path = None

    # Accept exact encrypted staging and return destination-owned evidence.
    def upload_artifact(self, staging_path, expected_sha256, _expected_hmac_sha256, expected_size):
        # Retain the exact created encrypted staging path.
        self.staging_path = Path(staging_path)
        # Require staging to exist until destination acknowledgement.
        self.staging_present_during_commit = self.staging_path.is_file()
        # Read only encrypted bytes for the synthetic adapter.
        self.encrypted_bytes = self.staging_path.read_bytes()
        # Optionally acknowledge another checksum to trigger fail-closed retention.
        acknowledged_sha256 = "f" * 64 if self.bad_upload else expected_sha256
        # Sign exact upload state under independent destination authority.
        self.acknowledgement = recovery.sign_evidence({"schema": "casino-off-instance-destination-ack-v1", "completed": True, "durable": True, "off_instance": True, "encrypted_artifact_sha256": acknowledged_sha256, "encrypted_size": expected_size, "acknowledged_at": "2026-07-16T20:00:00+00:00", "retention_until": "2026-07-23T20:00:00+00:00"}, DESTINATION_KEY)
        # Return the signed acknowledgement.
        return self.acknowledgement

    # Commit the signed manifest and return destination-owned metadata acknowledgement.
    def commit_manifest(self, _manifest_bytes, manifest_sha256, encrypted_artifact_sha256):
        # Require encrypted staging to remain until manifest commit acknowledgement.
        self.staging_present_during_commit = self.staging_present_during_commit and self.staging_path.is_file()
        # Optionally acknowledge another manifest digest.
        acknowledged_manifest = "e" * 64 if self.bad_manifest else manifest_sha256
        # Return exact signed commit evidence.
        return recovery.sign_evidence({"schema": "casino-off-instance-manifest-ack-v1", "completed": True, "durable": True, "off_instance": True, "manifest_sha256": acknowledged_manifest, "encrypted_artifact_sha256": encrypted_artifact_sha256}, DESTINATION_KEY)


# Raise after one authenticated chunk to model a broken clean-target client pipe.
class FailingSink(RetainedSink):
    # Reject the first write after retaining no bytes.
    def write(self, payload):
        # Raise a fixed synthetic pipe failure.
        raise BrokenPipeError("synthetic private process detail")


# Report a partial write after accepting only part of one authenticated chunk.
class ShortWritingSink(RetainedSink):
    # Accept all but one byte and report the exact short count.
    def write(self, payload):
        # Retain only a strict prefix to model a truncated target pipe.
        written = super().write(payload[:-1])
        # Return the actual partial count rather than falsely claiming completion.
        return written


# Model one cancellable watchdog returned by controlled tests.
class FakeTimer:
    # Initialize cancellation evidence.
    def __init__(self):
        # Track cancellation.
        self.cancelled = False

    # Record cancellation without starting a thread.
    def cancel(self):
        # Mark the timer cancelled.
        self.cancelled = True


# Build one signed post-restore #204 schema and representative-state result.
def signed_restore_result(manifest, authorization):
    # Sign exact bindings and timestamps under independent restore authority.
    return recovery.sign_evidence({
        # Identify the restore-result contract.
        "schema": "casino-clean-restore-result-v1",
        # Record completed wrapper and verifier state.
        "restore_completed": True,
        # Record exact #204 schema compatibility.
        "schema_compatible": True,
        # Record representative state compatibility.
        "representative_state_compatible": True,
        # Bind exact encrypted recovery point.
        "encrypted_artifact_sha256": manifest.encrypted_artifact_sha256,
        # Bind isolated target opaquely.
        "target_hmac_sha256": authorization.target_hmac_sha256,
        # Bind exact signed empty-target authorization.
        "authorization_sha256": authorization.evidence_sha256,
        # Bind immutable release SHA.
        "release_sha": manifest.release_sha,
        # Bind canonical application version.
        "app_version": manifest.app_version,
        # Bind #204 schema version.
        "mysql_schema_version": manifest.mysql_schema_version,
        # Bind #204 migration chain.
        "migration_chain_sha256": manifest.migration_chain_sha256,
        # Bind representative structural schema digest.
        "schema_state_sha256": "3" * 64,
        # Bind representative application state digest.
        "representative_state_sha256": "4" * 64,
        # Record actual restore start after recovery point completion.
        "restore_started_at": "2026-07-16T19:58:00+00:00",
        # Record actual restore completion at the decision time.
        "restore_completed_at": "2026-07-16T20:00:00+00:00",
    }, RESTORE_KEY)


# Verify fail-closed evidence contracts and secret-safe formatting.
class RecoveryEvidenceTests(unittest.TestCase):
    # Prove independent correctly sized keys remain fully redacted.
    def test_key_roles_and_redaction(self):
        # Construct valid independent keys.
        keys = recovery.RecoveryKeys(ENCRYPTION_KEY, EVIDENCE_KEY, DESTINATION_KEY, PROVIDER_KEY, RESTORE_KEY)
        # Require both common formatting paths to omit secret bytes.
        self.assertEqual(repr(keys), "<redacted recovery keys>")
        # Require ordinary string conversion to use the same fixed text.
        self.assertEqual(str(keys), "<redacted recovery keys>")
        # Reject cross-role key reuse.
        with self.assertRaisesRegex(recovery.RecoveryError, "independent"):
            # Supply identical values only inside the synthetic process.
            recovery.RecoveryKeys(ENCRYPTION_KEY, ENCRYPTION_KEY, DESTINATION_KEY, PROVIDER_KEY, RESTORE_KEY)
        # Reject a weak evidence key.
        with self.assertRaisesRegex(recovery.RecoveryError, "evidence key"):
            # Supply a deliberately short synthetic value.
            recovery.RecoveryKeys(ENCRYPTION_KEY, b"short", DESTINATION_KEY, PROVIDER_KEY, RESTORE_KEY)
        # Reject destination authority reuse with the manifest signer.
        with self.assertRaisesRegex(recovery.RecoveryError, "independent"):
            # Supply identical manifest and destination synthetic values.
            recovery.RecoveryKeys(ENCRYPTION_KEY, EVIDENCE_KEY, EVIDENCE_KEY, PROVIDER_KEY, RESTORE_KEY)

    # Prove any signed field edit invalidates provider evidence.
    def test_provider_tamper_fails_closed(self):
        # Sign a complete sanitized record.
        signed = recovery.sign_evidence(provider_record(), PROVIDER_KEY)
        # Change completion semantics after signing.
        signed["completed"] = False
        # Require complete-record integrity failure before semantic parsing.
        with self.assertRaisesRegex(recovery.RecoveryError, "integrity"):
            # Attempt to trust the altered record.
            recovery.validate_provider_evidence(signed, PROVIDER_KEY, NOW)

    # Prove stale or incomplete provider evidence cannot satisfy cutover.
    def test_provider_freshness_and_cost_semantics(self):
        # Sign and validate the current complete fixture.
        current = recovery.validate_provider_evidence(recovery.sign_evidence(provider_record(), PROVIDER_KEY), PROVIDER_KEY, NOW)
        # Require explicit successful semantics.
        self.assertTrue(current.completed and current.cost_included)
        # Build an observation older than the maximum accepted age.
        stale = provider_record()
        # Move both timestamps outside the freshness window.
        stale["completed_at"] = stale["verified_at"] = "2026-07-14T19:00:00+00:00"
        # Require stale evidence to keep the gate blocked.
        with self.assertRaisesRegex(recovery.RecoveryError, "stale"):
            # Validate the correctly signed but old record.
            recovery.validate_provider_evidence(recovery.sign_evidence(stale, PROVIDER_KEY), PROVIDER_KEY, NOW)
        # Remove required cost semantics entirely.
        incomplete = provider_record()
        # Delete the field rather than substituting an identifier.
        incomplete.pop("cost_included")
        # Require signed partial evidence to remain insufficient.
        with self.assertRaisesRegex(recovery.RecoveryError, "fields"):
            # Validate the correctly signed but partial record.
            recovery.validate_provider_evidence(recovery.sign_evidence(incomplete, PROVIDER_KEY), PROVIDER_KEY, NOW)
        # Record an explicit new-cost state that remains unauthorized.
        charged = provider_record()
        # Mark the provider backup outside the approved cost.
        charged["cost_included"] = False
        # Require a correctly signed new-cost state to keep the gate blocked.
        with self.assertRaisesRegex(recovery.RecoveryError, "incomplete"):
            # Validate the signed but unauthorized-cost record.
            recovery.validate_provider_evidence(recovery.sign_evidence(charged, PROVIDER_KEY), PROVIDER_KEY, NOW)
        # Reject naive decision times rather than applying local timezone policy.
        with self.assertRaisesRegex(recovery.RecoveryError, "timestamps"):
            # Supply a timezone-free synthetic decision instant.
            recovery.validate_provider_evidence(recovery.sign_evidence(provider_record(), PROVIDER_KEY), PROVIDER_KEY, datetime(2026, 7, 16, 20, 0))
        # Reject booleans even though Python treats them as integers.
        with self.assertRaisesRegex(recovery.RecoveryError, "age policy"):
            # Attempt to weaken the freshness bound with an ambiguous scalar.
            recovery.validate_provider_evidence(recovery.sign_evidence(provider_record(), PROVIDER_KEY), PROVIDER_KEY, NOW, True)

    # Prove exact encrypted artifact and release bindings are immutable.
    def test_recovery_manifest_tamper_and_fields(self):
        # Sign a complete manifest fixture.
        signed, acknowledgement = signed_manifest_pair()
        # Parse the valid record first.
        validated = recovery.validate_recovery_manifest(signed, EVIDENCE_KEY, acknowledgement, DESTINATION_KEY, NOW)
        # Require the distinct schema and artifact identities.
        self.assertEqual((validated.mysql_schema_version, validated.encrypted_size), (2, 512))
        # Copy before changing the acknowledged encrypted checksum.
        tampered = copy.deepcopy(signed)
        # Substitute another syntactically valid artifact identity.
        tampered["encrypted_artifact_sha256"] = "f" * 64
        # Require the complete evidence HMAC to reject it.
        with self.assertRaisesRegex(recovery.RecoveryError, "integrity"):
            # Attempt to trust the altered manifest.
            recovery.validate_recovery_manifest(tampered, EVIDENCE_KEY, acknowledgement, DESTINATION_KEY, NOW)
        # Build a correctly signed manifest with contradictory timing.
        reversed_times = manifest_record()
        # Put acknowledgement before artifact completion.
        reversed_times["destination_acknowledged_at"] = "2026-07-16T19:00:00+00:00"
        # Require semantic refusal even with a valid signature.
        with self.assertRaisesRegex(recovery.RecoveryError, "timestamps"):
            # Validate the contradictory record.
            recovery.validate_recovery_manifest(recovery.sign_evidence(reversed_times, EVIDENCE_KEY), EVIDENCE_KEY, acknowledgement, DESTINATION_KEY, NOW)
        # Sign a syntactically complete acknowledgement with the wrong authority.
        wrong_authority_ack = recovery.sign_evidence({key: value for key, value in signed_destination_ack().items() if key != recovery.SIGNATURE_FIELD}, EVIDENCE_KEY)
        # Require the manifest signer to be unable to forge destination completion.
        with self.assertRaisesRegex(recovery.RecoveryError, "integrity"):
            # Pair the valid manifest with the wrong-authority acknowledgement.
            recovery.validate_recovery_manifest(signed, EVIDENCE_KEY, wrong_authority_ack, DESTINATION_KEY, NOW)
        # Change retention under the real destination authority after manifest signing.
        changed_ack_fields = {key: value for key, value in acknowledgement.items() if key != recovery.SIGNATURE_FIELD}
        # Extend retention to create another valid but different acknowledgement.
        changed_ack_fields["retention_until"] = "2026-07-24T19:35:00+00:00"
        # Sign the changed acknowledgement with the correct independent key.
        changed_ack = recovery.sign_evidence(changed_ack_fields, DESTINATION_KEY)
        # Require exact acknowledgement digest pairing, not merely valid destination authority.
        with self.assertRaisesRegex(recovery.RecoveryError, "destination acknowledgement"):
            # Pair the old manifest with newly signed different retention.
            recovery.validate_recovery_manifest(signed, EVIDENCE_KEY, changed_ack, DESTINATION_KEY, NOW)

    # Prove evidence-only health checks reject a foreign #204 schema contract.
    def test_manifest_rejects_foreign_packaged_schema(self):
        # Build one valid manifest paired to exact destination evidence.
        signed, acknowledgement = signed_manifest_pair()
        # Copy only unsigned manifest fields for independently signed mutation.
        baseline = {key: value for key, value in signed.items() if key != recovery.SIGNATURE_FIELD}
        # Exercise both independent packaged schema bindings.
        for field, value in (("mysql_schema_version", 3), ("migration_chain_sha256", "c" * 64)):
            # Name the changed binding in unittest diagnostics.
            with self.subTest(field=field):
                # Copy the valid manifest for one isolated foreign-contract mutation.
                foreign = dict(baseline)
                # Replace exactly one packaged #204 binding.
                foreign[field] = value
                # Require a validly re-signed foreign manifest to fail closed.
                with self.assertRaisesRegex(recovery.RecoveryError, "packaged MySQL schema"):
                    # Use the same valid destination evidence to isolate schema compatibility.
                    recovery.validate_recovery_manifest(recovery.sign_evidence(foreign, EVIDENCE_KEY), EVIDENCE_KEY, acknowledgement, DESTINATION_KEY, NOW)

    # Prove hostile field values never enter recovery diagnostics.
    def test_errors_do_not_echo_hostile_values(self):
        # Create a hostile untrusted field that resembles private material.
        hostile = {"schema": "private-target-path-and-secret", recovery.SIGNATURE_FIELD: "not-a-digest"}
        # Capture the fixed integrity failure.
        with self.assertRaises(recovery.RecoveryError) as context:
            # Attempt validation with malformed evidence.
            recovery.validate_recovery_manifest(hostile, EVIDENCE_KEY, signed_destination_ack(), DESTINATION_KEY, NOW)
        # Require the hostile value to be absent from the diagnostic.
        self.assertNotIn("private-target-path-and-secret", str(context.exception))

    # Prove streaming AES-GCM round-trips without buffering or plaintext disk output.
    def test_streaming_encryption_verifies_before_restore(self):
        # Build a logical stream larger than one fixed chunk.
        plaintext = (b"synthetic logical backup row\n" * 5000)
        # Create one sanitized release/schema/target context.
        context = {"release_sha": "b" * 40, "app_version": "9.2.0", "mysql_schema_version": 2, "migration_chain_sha256": MIGRATION_CHAIN, "source_target_hmac_sha256": "d" * 64}
        # Encrypt directly between in-memory binary streams.
        encrypted = io.BytesIO()
        # Record encryption metadata without retaining plaintext.
        metadata = recovery.encrypt_stream(io.BytesIO(plaintext), encrypted, ENCRYPTION_KEY, context)
        # Compute exact public and keyed artifact identities.
        artifact_sha256, artifact_hmac_sha256, artifact_size = recovery.encrypted_artifact_identity(encrypted, EVIDENCE_KEY)
        # Restore only after a complete no-output verification pass.
        restored = io.BytesIO()
        # Run the two-pass verify-then-release operation.
        verified = recovery.decrypt_verified_stream(encrypted, restored, ENCRYPTION_KEY, EVIDENCE_KEY, artifact_sha256, artifact_hmac_sha256, artifact_size, metadata["encryption_header_sha256"], context)
        # Require byte-exact logical restore output.
        self.assertEqual(restored.getvalue(), plaintext)
        # Require representative digest and length evidence.
        self.assertEqual((verified["plaintext_sha256"], verified["plaintext_size"]), (metadata["plaintext_sha256"], len(plaintext)))

    # Prove encrypted staging framing cannot silently accept a partial write.
    def test_streaming_encryption_rejects_short_staging_write(self):
        # Build one exact packaged release and schema context.
        context = {"release_sha": "b" * 40, "app_version": "9.2.0", "mysql_schema_version": 2, "migration_chain_sha256": MIGRATION_CHAIN, "source_target_hmac_sha256": "d" * 64}
        # Use a sink that accepts only a strict prefix of its first write.
        target = ShortWritingSink()
        # Require fixed staging failure before any artifact can be accepted.
        with self.assertRaisesRegex(recovery.RecoveryError, "staging write failed"):
            # Attempt to encrypt representative synthetic logical bytes.
            recovery.encrypt_stream(io.BytesIO(b"synthetic recovery content"), target, ENCRYPTION_KEY, context)
        # Prove a partial prefix was observed rather than accepted as complete framing.
        self.assertGreater(len(target.getvalue()), 0)

    # Prove ciphertext and authenticated context tampering release no plaintext.
    def test_streaming_tamper_fails_before_output(self):
        # Build a compact synthetic logical dump.
        plaintext = b"synthetic recovery content"
        # Bind a synthetic exact release context.
        context = {"release_sha": "b" * 40, "app_version": "9.2.0", "mysql_schema_version": 2, "migration_chain_sha256": MIGRATION_CHAIN, "source_target_hmac_sha256": "d" * 64}
        # Encrypt the source into one binary artifact.
        encrypted = io.BytesIO()
        # Capture exact authenticated header metadata.
        metadata = recovery.encrypt_stream(io.BytesIO(plaintext), encrypted, ENCRYPTION_KEY, context)
        # Compute and verify the original artifact before simulating later mutation.
        original_sha256, original_hmac_sha256, original_size = recovery.encrypted_artifact_identity(encrypted, EVIDENCE_KEY)
        # Complete a successful no-output preverification pass.
        recovery.verify_encrypted_stream(encrypted, ENCRYPTION_KEY, EVIDENCE_KEY, original_sha256, original_hmac_sha256, original_size, metadata["encryption_header_sha256"], context)
        # Extract mutable test bytes only inside the synthetic process.
        changed = bytearray(encrypted.getvalue())
        # Decode the authenticated public header length.
        header_size = struct.unpack(">I", changed[len(recovery.ENCRYPTED_STREAM_MAGIC):len(recovery.ENCRYPTED_STREAM_MAGIC) + 4])[0]
        # Locate the first data record's ciphertext after framing and record header.
        first_ciphertext_offset = len(recovery.ENCRYPTED_STREAM_MAGIC) + 4 + header_size + recovery.RECORD_HEADER.size
        # Flip one byte in the first independently authenticated chunk.
        changed[first_ciphertext_offset] ^= 1
        # Recompute public identities to model coherent destination metadata tampering.
        tampered_stream = io.BytesIO(bytes(changed))
        # Compute identities for the altered bytes.
        sha256, hmac_sha256, size = recovery.encrypted_artifact_identity(tampered_stream, EVIDENCE_KEY)
        # Provide an output sink that must remain empty.
        output = io.BytesIO()
        # Require GCM authentication failure before the second pass starts.
        with self.assertRaisesRegex(recovery.RecoveryError, "authentication"):
            # Attempt restore of coherently re-described but unauthenticated ciphertext.
            recovery.decrypt_verified_stream(tampered_stream, output, ENCRYPTION_KEY, EVIDENCE_KEY, sha256, hmac_sha256, size, metadata["encryption_header_sha256"], context)
        # Prove no plaintext reached the restore sink.
        self.assertEqual(output.getvalue(), b"")

    # Prove strict authenticated context allowlisting excludes private additions.
    def test_streaming_context_rejects_extra_fields(self):
        # Build the complete allowed public context.
        context = {"release_sha": "b" * 40, "app_version": "9.2.0", "mysql_schema_version": 2, "migration_chain_sha256": "c" * 64, "source_target_hmac_sha256": "d" * 64}
        # Add a field that could otherwise carry private configuration.
        context["private_path"] = "host-private-value"
        # Require refusal before any logical bytes are encrypted.
        with self.assertRaisesRegex(recovery.RecoveryError, "context"):
            # Attempt to construct an artifact header with extra context.
            recovery.encrypt_stream(io.BytesIO(b"synthetic"), io.BytesIO(), ENCRYPTION_KEY, context)

    # Prove every signed evidence class rejects extra private fields.
    def test_signed_contracts_reject_extra_fields(self):
        # Add a private field to otherwise valid provider evidence.
        provider = provider_record()
        # Simulate an identifier that must never enter evidence.
        provider["provider_object"] = "private"
        # Require exact provider allowlist enforcement.
        with self.assertRaisesRegex(recovery.RecoveryError, "fields"):
            # Validate the correctly signed but extended provider record.
            recovery.validate_provider_evidence(recovery.sign_evidence(provider, PROVIDER_KEY), PROVIDER_KEY, NOW)
        # Add a private field to otherwise valid destination evidence.
        destination = {key: value for key, value in signed_destination_ack().items() if key != recovery.SIGNATURE_FIELD}
        # Simulate a private destination label.
        destination["destination_object"] = "private"
        # Require exact destination allowlist enforcement.
        with self.assertRaisesRegex(recovery.RecoveryError, "fields"):
            # Validate the correctly destination-signed but extended record.
            recovery.validate_destination_acknowledgement(recovery.sign_evidence(destination, DESTINATION_KEY), DESTINATION_KEY, "a" * 64, 512, NOW)
        # Build a valid paired manifest and acknowledgement.
        manifest, acknowledgement = signed_manifest_pair()
        # Extend the unsigned manifest with a private field.
        extended_manifest = {key: value for key, value in manifest.items() if key != recovery.SIGNATURE_FIELD}
        # Simulate a private configuration path.
        extended_manifest["private_path"] = "private"
        # Require exact manifest allowlist enforcement.
        with self.assertRaisesRegex(recovery.RecoveryError, "fields"):
            # Validate the correctly manifest-signed but extended record.
            recovery.validate_recovery_manifest(recovery.sign_evidence(extended_manifest, EVIDENCE_KEY), EVIDENCE_KEY, acknowledgement, DESTINATION_KEY, NOW)
        # Extend an otherwise valid clean-target authorization.
        authorization_fields = {key: value for key, value in signed_restore_authorization().items() if key != recovery.SIGNATURE_FIELD}
        # Simulate an ambient database identifier.
        authorization_fields["database"] = "private"
        # Require exact restore authorization allowlist enforcement.
        with self.assertRaisesRegex(recovery.RecoveryError, "fields"):
            # Validate the independently signed but extended authorization.
            recovery.validate_restore_authorization(recovery.sign_evidence(authorization_fields, RESTORE_KEY), RESTORE_KEY, "9" * 64, NOW)

    # Prove destination retention remains bounded to the reviewed 7-35 day window.
    def test_destination_retention_bounds(self):
        # Copy a complete valid destination record without its signature.
        fields = {key: value for key, value in signed_destination_ack().items() if key != recovery.SIGNATURE_FIELD}
        # Shorten retention below seven days.
        fields["retention_until"] = "2026-07-17T19:35:00+00:00"
        # Require too-short retention to block the gate.
        with self.assertRaisesRegex(recovery.RecoveryError, "retention policy"):
            # Validate the correctly signed short-retention record.
            recovery.validate_destination_acknowledgement(recovery.sign_evidence(fields, DESTINATION_KEY), DESTINATION_KEY, "a" * 64, 512, NOW)
        # Extend retention beyond thirty-five days.
        fields["retention_until"] = "2026-09-01T19:35:00+00:00"
        # Require unbounded retention to violate the reviewed policy.
        with self.assertRaisesRegex(recovery.RecoveryError, "retention policy"):
            # Validate the correctly signed overlong record.
            recovery.validate_destination_acknowledgement(recovery.sign_evidence(fields, DESTINATION_KEY), DESTINATION_KEY, "a" * 64, 512, NOW)

    # Prove age alerts and RPO/RTO are derived from signed timestamps.
    def test_recovery_age_and_restore_timing(self):
        # Build real encrypted and paired evidence.
        _plaintext, _artifact, _context, manifest_record_value, ack_record = encrypted_recovery_bundle()
        # Validate paired manifest evidence.
        manifest = recovery.validate_recovery_manifest(manifest_record_value, EVIDENCE_KEY, ack_record, DESTINATION_KEY, NOW)
        # Validate the independent empty-target authorization.
        authorization = recovery.validate_restore_authorization(signed_restore_authorization(), RESTORE_KEY, "9" * 64, NOW)
        # Validate post-restore evidence and recompute timing.
        result = recovery.validate_restore_result(signed_restore_result(manifest, authorization), RESTORE_KEY, manifest, authorization, NOW)
        # Require derived 28-minute RPO and 2-minute RTO.
        self.assertEqual((result.observed_rpo_seconds, result.observed_rto_seconds), (28 * 60, 2 * 60))
        # Require a two-day-old recovery point to trigger the one-day alert.
        with self.assertRaisesRegex(recovery.RecoveryError, "age alert"):
            # Evaluate at a deterministic stale time while retention remains active.
            recovery.validate_recovery_age(manifest, datetime(2026, 7, 18, 20, 0, tzinfo=timezone.utc))

    # Prove signed download completion is bounded by this exact operation.
    def test_download_receipt_timing_is_bounded_by_operation(self):
        # Build one exact synthetic encrypted recovery point.
        _plaintext, artifact, _context, manifest_record_value, acknowledgement = encrypted_recovery_bundle()
        # Validate its signed manifest and destination acknowledgement at preflight.
        manifest = recovery.validate_recovery_manifest(manifest_record_value, EVIDENCE_KEY, acknowledgement, DESTINATION_KEY, NOW)
        # Fix a post-download validation boundary after the preflight decision.
        receipt_validation_time = datetime(2026, 7, 16, 20, 0, 2, tzinfo=timezone.utc)
        # Create one isolated encrypted-only staging directory.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve the isolated staging directory.
            staging = Path(temporary_directory)
            # Configure absolute synthetic wrappers without invoking either process.
            config = recovery.RecoveryProcessConfig(staging / "dump-wrapper", staging / "restore-wrapper", staging, {}, 30)
            # Sign valid completion after preflight and before post-download validation.
            valid_destination = SyntheticDestination(artifact, "2026-07-16T20:00:01+00:00")
            # Download and validate the exact encrypted artifact.
            staging_path = recovery.download_encrypted_staging(config, recovery_keys(), manifest, valid_destination, receipt_validation_time, NOW)
            # Require byte-exact encrypted staging for the valid receipt.
            self.assertEqual(staging_path.read_bytes(), artifact)
            # Remove only this test's accepted encrypted staging file.
            staging_path.unlink()
            # Exercise signed receipt replay before operation start and future completion after validation.
            for invalid_timestamp in ("2026-07-16T19:59:59+00:00", "2026-07-16T20:00:03+00:00"):
                # Create one independently signed invalid timing case.
                invalid_destination = SyntheticDestination(artifact, invalid_timestamp)
                # Require stale and future receipts to fail closed identically.
                with self.assertRaisesRegex(recovery.RecoveryError, "receipt timestamps"):
                    # Attempt the exact encrypted download under fixed operation boundaries.
                    recovery.download_encrypted_staging(config, recovery_keys(), manifest, invalid_destination, receipt_validation_time, NOW)
                # Require rejected encrypted staging cleanup after each failure.
                self.assertEqual(list(staging.iterdir()), [])

    # Prove argv-free restore succeeds and leaves no plaintext or encrypted staging.
    def test_clean_restore_orchestration_success(self):
        # Build one complete synthetic encrypted recovery bundle.
        plaintext, artifact, context, manifest, acknowledgement = encrypted_recovery_bundle()
        # Create one isolated operating-system temporary directory.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve the isolated staging directory.
            staging = Path(temporary_directory)
            # Configure only absolute preconfigured wrapper paths and synthetic environment.
            config = recovery.RecoveryProcessConfig(staging / "dump-wrapper", staging / "restore-wrapper", staging, {}, 30)
            # Create one successful deterministic restore child.
            process = FakeRestoreProcess()
            # Use only the synthetic memory destination.
            destination = SyntheticDestination(artifact)
            # Patch process creation without weakening production argv behavior.
            with mock.patch.object(recovery.subprocess, "Popen", return_value=process) as popen:
                # Execute complete preverified clean-target restore orchestration.
                result = recovery.restore_clean_target(config, recovery_keys(), manifest, acknowledgement, signed_restore_authorization(), "9" * 64, destination, context, signed_restore_result, NOW)
            # Require exactly one no-argument restore wrapper invocation.
            self.assertEqual(popen.call_args.args[0], [str(config.restore_program)])
            # Require byte-exact representative logical restore input.
            self.assertEqual(process.stdin.getvalue(), plaintext)
            # Require derived timing evidence.
            self.assertEqual(result.observed_rto_seconds, 120)
            # Require no plaintext or encrypted staging file remains.
            self.assertEqual(list(staging.iterdir()), [])

    # Prove the complete backup pipeline retains no plaintext and cleans after both acknowledgements.
    def test_backup_orchestration_success(self):
        # Use representative synthetic logical rows only.
        logical = b"synthetic-user\tsynthetic-wallet\tsynthetic-ledger\n"
        # Bind exact release and #204 schema context.
        context = {"release_sha": "b" * 40, "app_version": "9.2.0", "mysql_schema_version": 2, "migration_chain_sha256": MIGRATION_CHAIN, "source_target_hmac_sha256": "d" * 64}
        # Create one isolated encrypted-staging directory.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve the isolated staging directory.
            staging = Path(temporary_directory)
            # Configure absolute argv-free wrapper paths.
            config = recovery.RecoveryProcessConfig(staging / "dump-wrapper", staging / "restore-wrapper", staging, {}, 30)
            # Create a successful deterministic dump child.
            process = FakeDumpProcess(logical)
            # Create a successful destination adapter.
            destination = SyntheticUploadDestination()
            # Patch only child process creation.
            with mock.patch.object(recovery.subprocess, "Popen", return_value=process) as popen:
                # Complete encrypted backup, upload, and manifest commit.
                manifest_record_value = recovery.complete_off_instance_backup(config, recovery_keys(), context, destination, NOW)
            # Require exactly one no-argument dump wrapper invocation.
            self.assertEqual(popen.call_args.args[0], [str(config.dump_program)])
            # Require encrypted staging remained through both acknowledgements.
            self.assertTrue(destination.staging_present_during_commit)
            # Require no plaintext logical bytes appear in uploaded ciphertext.
            self.assertNotIn(logical, destination.encrypted_bytes)
            # Require no local plaintext or encrypted staging remains after commit acknowledgement.
            self.assertEqual(list(staging.iterdir()), [])
            # Validate the signed manifest paired to exact destination evidence.
            manifest = recovery.validate_recovery_manifest(manifest_record_value, EVIDENCE_KEY, destination.acknowledgement, DESTINATION_KEY, NOW)
            # Require exact logical, release, and schema bindings.
            self.assertEqual((manifest.logical_plaintext_size, manifest.release_sha, manifest.mysql_schema_version, manifest.migration_chain_sha256), (len(logical), context["release_sha"], 2, MIGRATION_CHAIN))

    # Prove failed destination acknowledgements retain encrypted staging for retry only.
    def test_backup_bad_ack_retains_only_encrypted_staging(self):
        # Use one synthetic logical stream.
        logical = b"synthetic private logical content"
        # Bind exact release and #204 schema context.
        context = {"release_sha": "b" * 40, "app_version": "9.2.0", "mysql_schema_version": 2, "migration_chain_sha256": MIGRATION_CHAIN, "source_target_hmac_sha256": "d" * 64}
        # Exercise both artifact and manifest acknowledgement failures.
        for bad_upload, bad_manifest in ((True, False), (False, True)):
            # Create a new isolated staging directory for each failure.
            with tempfile.TemporaryDirectory() as temporary_directory:
                # Resolve isolated staging.
                staging = Path(temporary_directory)
                # Configure absolute synthetic wrappers.
                config = recovery.RecoveryProcessConfig(staging / "dump-wrapper", staging / "restore-wrapper", staging, {}, 30)
                # Create the selected destination failure.
                destination = SyntheticUploadDestination(bad_upload, bad_manifest)
                # Patch only child process creation.
                with mock.patch.object(recovery.subprocess, "Popen", return_value=FakeDumpProcess(logical)):
                    # Require fail-closed destination acknowledgement behavior.
                    with self.assertRaises(recovery.RecoveryError):
                        # Attempt complete backup.
                        recovery.complete_off_instance_backup(config, recovery_keys(), context, destination, NOW)
                # Require exactly one encrypted staging file remains for retry/quarantine.
                retained = list(staging.iterdir())
                # Verify bounded retention count.
                self.assertEqual(len(retained), 1)
                # Require retained ciphertext not to contain plaintext logical bytes.
                self.assertNotIn(logical, retained[0].read_bytes())

    # Prove dump nonzero and whole-stream timeout remove partial ciphertext and produce no manifest.
    def test_backup_process_failure_and_timeout_remove_partial(self):
        # Use one synthetic logical stream.
        logical = b"synthetic logical content"
        # Bind exact release and #204 schema context.
        context = {"release_sha": "b" * 40, "app_version": "9.2.0", "mysql_schema_version": 2, "migration_chain_sha256": MIGRATION_CHAIN, "source_target_hmac_sha256": "d" * 64}
        # Exercise nonzero and watchdog timeout separately.
        for timed_out in (False, True):
            # Create a new isolated staging directory.
            with tempfile.TemporaryDirectory() as temporary_directory:
                # Resolve isolated staging.
                staging = Path(temporary_directory)
                # Configure bounded synthetic wrappers.
                config = recovery.RecoveryProcessConfig(staging / "dump-wrapper", staging / "restore-wrapper", staging, {}, 1)
                # Use nonzero status unless the watchdog simulates timeout.
                process = FakeDumpProcess(logical, 1 if not timed_out else 0)
                # Build patch contexts for process creation.
                popen_patch = mock.patch.object(recovery.subprocess, "Popen", return_value=process)
                # Start the process patch.
                with popen_patch:
                    # Use a real watchdog for nonzero and a fired watchdog for timeout.
                    if timed_out:
                        # Define deterministic timeout behavior.
                        def timeout_watchdog(child, _timeout):
                            # Kill the exact tracked dump child.
                            child.kill()
                            # Mark timeout before pipeline completion.
                            flag = threading.Event()
                            # Set the timeout flag.
                            flag.set()
                            # Return controlled timer state.
                            return flag, FakeTimer()
                        # Patch the watchdog only for the timeout case.
                        watchdog_patch = mock.patch.object(recovery, "_start_process_watchdog", side_effect=timeout_watchdog)
                    else:
                        # Use a no-op context manager for the nonzero case.
                        watchdog_patch = mock.patch.object(recovery, "_start_process_watchdog", wraps=recovery._start_process_watchdog)
                    # Apply the selected watchdog behavior.
                    with watchdog_patch:
                        # Require fixed process failure without destination calls.
                        with self.assertRaises(recovery.RecoveryError):
                            # Attempt encrypted staging creation.
                            recovery.create_encrypted_staging(config, recovery_keys(), context)
                # Require no partial encrypted or plaintext file remains.
                self.assertEqual(list(staging.iterdir()), [])

    # Prove partial restore failures kill/reap and require target quarantine.
    def test_clean_restore_failure_requires_quarantine(self):
        # Build one complete synthetic encrypted recovery bundle.
        _plaintext, artifact, context, manifest, acknowledgement = encrypted_recovery_bundle()
        # Create one isolated staging directory.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve the isolated staging directory.
            staging = Path(temporary_directory)
            # Configure absolute synthetic wrapper paths.
            config = recovery.RecoveryProcessConfig(staging / "dump-wrapper", staging / "restore-wrapper", staging, {}, 30)
            # Fail the restore pipe before accepting the first authenticated chunk.
            process = FakeRestoreProcess(FailingSink())
            # Patch only process creation.
            with mock.patch.object(recovery.subprocess, "Popen", return_value=process):
                # Require mandatory quarantine rather than raw pipe details.
                with self.assertRaisesRegex(recovery.RecoveryQuarantineRequired, "quarantine"):
                    # Attempt the isolated restore.
                    recovery.restore_clean_target(config, recovery_keys(), manifest, acknowledgement, signed_restore_authorization(), "9" * 64, SyntheticDestination(artifact), context, signed_restore_result, NOW)
            # Require tracked child kill and reap.
            self.assertTrue(process.killed and process.waited)
            # Require encrypted download staging cleanup with no plaintext file.
            self.assertEqual(list(staging.iterdir()), [])

    # Prove a short authenticated-chunk write cannot be counted as a complete restore.
    def test_clean_restore_short_write_requires_quarantine(self):
        # Build one complete synthetic encrypted recovery bundle.
        plaintext, artifact, context, manifest, acknowledgement = encrypted_recovery_bundle()
        # Create one isolated staging directory.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve the isolated staging directory.
            staging = Path(temporary_directory)
            # Configure absolute synthetic wrapper paths.
            config = recovery.RecoveryProcessConfig(staging / "dump-wrapper", staging / "restore-wrapper", staging, {}, 30)
            # Accept only part of the first authenticated chunk.
            process = FakeRestoreProcess(ShortWritingSink())
            # Patch only process creation under the real authenticated stream path.
            with mock.patch.object(recovery.subprocess, "Popen", return_value=process):
                # Require mandatory quarantine after any partial target emission.
                with self.assertRaisesRegex(recovery.RecoveryQuarantineRequired, "quarantine"):
                    # Attempt the isolated clean-target restore.
                    recovery.restore_clean_target(config, recovery_keys(), manifest, acknowledgement, signed_restore_authorization(), "9" * 64, SyntheticDestination(artifact), context, signed_restore_result, NOW)
            # Require a strict partial prefix rather than falsely complete output.
            self.assertEqual(process.stdin.getvalue(), plaintext[:-1])
            # Require tracked child kill and reap after the short write.
            self.assertTrue(process.killed and process.waited)
            # Require encrypted download staging cleanup.
            self.assertEqual(list(staging.iterdir()), [])

    # Prove the whole-stream watchdog timeout blocks completion and quarantines target.
    def test_clean_restore_timeout_requires_quarantine(self):
        # Build one complete synthetic encrypted recovery bundle.
        _plaintext, artifact, context, manifest, acknowledgement = encrypted_recovery_bundle()
        # Create one isolated staging directory.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve the isolated staging directory.
            staging = Path(temporary_directory)
            # Configure one-second synthetic timeout policy.
            config = recovery.RecoveryProcessConfig(staging / "dump-wrapper", staging / "restore-wrapper", staging, {}, 1)
            # Create a synthetic child that the watchdog will kill.
            process = FakeRestoreProcess()
            # Model an already-fired whole-operation watchdog.
            def timed_out_watchdog(child, _timeout):
                # Kill the exact tracked child.
                child.kill()
                # Mark the timeout flag.
                flag = threading.Event()
                # Set the flag before returning.
                flag.set()
                # Return a cancellable synthetic timer.
                return flag, FakeTimer()
            # Patch process creation and watchdog timing deterministically.
            with mock.patch.object(recovery.subprocess, "Popen", return_value=process), mock.patch.object(recovery, "_start_process_watchdog", side_effect=timed_out_watchdog):
                # Require mandatory quarantine on whole-stream timeout.
                with self.assertRaisesRegex(recovery.RecoveryQuarantineRequired, "quarantine"):
                    # Attempt the isolated restore.
                    recovery.restore_clean_target(config, recovery_keys(), manifest, acknowledgement, signed_restore_authorization(), "9" * 64, SyntheticDestination(artifact), context, signed_restore_result, NOW)
            # Require exact child kill and reap behavior.
            self.assertTrue(process.killed and process.waited)

    # Prove a late-record mutation after preverify yields partial safe emission then quarantine.
    def test_late_record_mutation_requires_quarantine(self):
        # Build three independently authenticated chunks.
        logical = b"A" * recovery.STREAM_CHUNK_BYTES + b"B" * recovery.STREAM_CHUNK_BYTES + b"C" * 100
        # Build a complete bundle over the multi-chunk logical stream.
        _plaintext, artifact, context, manifest, acknowledgement = encrypted_recovery_bundle(logical)
        # Preserve the real exact-identity implementation.
        real_identity = recovery.encrypted_artifact_identity
        # Count preverify and restore-pass identity checks.
        calls = {"count": 0}
        # Mutate the second record only between preverification and restore processing.
        def identity_with_late_mutation(source, key):
            # Advance the identity-call counter.
            calls["count"] += 1
            # Run the real identity check on the preverification pass.
            if calls["count"] == 1:
                # Return exact original identity.
                return real_identity(source, key)
            # Read exact framing to locate the second data record.
            source.seek(0)
            # Read exact artifact bytes for bounded test mutation.
            payload = bytearray(source.read())
            # Decode header length.
            header_size = struct.unpack(">I", payload[len(recovery.ENCRYPTED_STREAM_MAGIC):len(recovery.ENCRYPTED_STREAM_MAGIC) + 4])[0]
            # Locate the first record header.
            first_header_offset = len(recovery.ENCRYPTED_STREAM_MAGIC) + 4 + header_size
            # Decode first record ciphertext length.
            _kind, _index, _plain_length, first_cipher_length = recovery.RECORD_HEADER.unpack(payload[first_header_offset:first_header_offset + recovery.RECORD_HEADER.size])
            # Locate second record ciphertext start.
            second_header_offset = first_header_offset + recovery.RECORD_HEADER.size + first_cipher_length
            # Flip one byte after the second public record header.
            payload[second_header_offset + recovery.RECORD_HEADER.size] ^= 1
            # Replace encrypted staging bytes after complete preverification.
            with open(source.name, "r+b") as mutable:
                # Write the same-length mutated ciphertext.
                mutable.write(payload)
                # Flush mutation before record processing.
                mutable.flush()
            # Rewind the existing stream handle.
            source.seek(0)
            # Model a TOCTOU attacker that bypassed only the outer identity check.
            return (manifest["encrypted_artifact_sha256"], manifest["encrypted_artifact_hmac_sha256"], manifest["encrypted_size"])
        # Create isolated staging and process sink.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve isolated staging.
            staging = Path(temporary_directory)
            # Configure synthetic no-argument wrappers.
            config = recovery.RecoveryProcessConfig(staging / "dump-wrapper", staging / "restore-wrapper", staging, {}, 30)
            # Retain bytes accepted before the modified second chunk.
            process = FakeRestoreProcess()
            # Patch exact identity only during orchestration.
            with mock.patch.object(recovery.subprocess, "Popen", return_value=process), mock.patch.object(recovery, "encrypted_artifact_identity", side_effect=identity_with_late_mutation):
                # Require target quarantine on late authenticated-record failure.
                with self.assertRaisesRegex(recovery.RecoveryQuarantineRequired, "quarantine"):
                    # Attempt the isolated restore.
                    recovery.restore_clean_target(config, recovery_keys(), manifest, acknowledgement, signed_restore_authorization(), "9" * 64, SyntheticDestination(artifact), context, signed_restore_result, NOW)
            # Require only the first unmodified authenticated chunk was emitted.
            self.assertEqual(process.stdin.getvalue(), b"A" * recovery.STREAM_CHUNK_BYTES)
            # Require kill/reap after partial target mutation.
            self.assertTrue(process.killed and process.waited)

    # Prove cleanup failure cannot replace mandatory quarantine diagnostics.
    def test_quarantine_diagnostic_survives_cleanup_failure(self):
        # Build one complete synthetic encrypted bundle.
        _plaintext, artifact, context, manifest, acknowledgement = encrypted_recovery_bundle()
        # Create isolated staging.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve isolated staging.
            staging = Path(temporary_directory)
            # Configure synthetic wrappers.
            config = recovery.RecoveryProcessConfig(staging / "dump-wrapper", staging / "restore-wrapper", staging, {}, 30)
            # Fail after child creation.
            process = FakeRestoreProcess(FailingSink())
            # Patch cleanup to fail after the restore failure.
            with mock.patch.object(recovery.subprocess, "Popen", return_value=process), mock.patch.object(recovery, "_remove_created_staging", side_effect=recovery.RecoveryError("private cleanup detail")):
                # Require the fixed quarantine message to remain dominant.
                with self.assertRaisesRegex(recovery.RecoveryQuarantineRequired, "target quarantine is required") as context_manager:
                    # Attempt the isolated restore.
                    recovery.restore_clean_target(config, recovery_keys(), manifest, acknowledgement, signed_restore_authorization(), "9" * 64, SyntheticDestination(artifact), context, signed_restore_result, NOW)
            # Require private cleanup detail to remain absent.
            self.assertNotIn("private cleanup detail", str(context_manager.exception))

    # Prove process environments accept text only and stay redacted.
    def test_process_environment_is_typed_and_redacted(self):
        # Create one temporary absolute staging path.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve the isolated directory.
            staging = Path(temporary_directory)
            # Reject a non-text environment value without echoing it.
            with self.assertRaisesRegex(recovery.RecoveryError, "environment"):
                # Supply an invalid synthetic scalar.
                recovery.RecoveryProcessConfig(staging / "dump", staging / "restore", staging, {"PRIVATE": object()}, 30)
            # Construct valid text-only configuration.
            config = recovery.RecoveryProcessConfig(staging / "dump", staging / "restore", staging, {"PRIVATE": "secret"}, 30)
            # Require fixed redaction for paths and environment values.
            self.assertEqual(repr(config), "<redacted recovery process configuration>")

    # Prove CLI wrappers receive only the explicit external environment allowlist.
    def test_cli_process_environment_does_not_inherit_ambient_secrets(self):
        # Create one isolated external configuration directory.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve the directory.
            root = Path(temporary_directory)
            # Write only one synthetic nonsecret wrapper setting.
            environment_path = root / "process-environment.json"
            # Persist the explicit text-to-text child environment.
            environment_path.write_text('{"WRAPPER_MODE":"synthetic"}', encoding="utf-8")
            # Build parent environment containing unrelated and recovery-key sentinels.
            parent_environment = {"CASINO_RECOVERY_DUMP_PROGRAM": str(root / "dump"), "CASINO_RECOVERY_RESTORE_PROGRAM": str(root / "restore"), "CASINO_RECOVERY_STAGING_DIRECTORY": str(root), "CASINO_RECOVERY_PROCESS_ENV_PATH": str(environment_path), "CASINO_RECOVERY_ENCRYPTION_KEY_B64": "ambient-key-sentinel", "AMBIENT_PRIVATE_SENTINEL": "ambient-secret"}
            # Replace the ambient environment for deterministic loading.
            with mock.patch.dict(recovery_cli.os.environ, parent_environment, clear=True):
                # Load the redacted process configuration.
                config = recovery_cli.load_process_config()
            # Require only explicit external mapping content.
            self.assertEqual(dict(config.process_environment), {"WRAPPER_MODE": "synthetic"})


# Run only this focused module when invoked directly.
if __name__ == "__main__":
    # Exit with unittest's standard status.
    unittest.main()
