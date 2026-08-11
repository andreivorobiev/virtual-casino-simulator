# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Secret-safe recovery evidence contracts for MYSQL-006 and TOOL-004."""

# Import annotations so immutable records can reference their own types.
from __future__ import annotations
# Import UTC-aware timestamps for bounded evidence freshness checks.
from datetime import datetime, timezone
# Import base64 for nonce transport inside the authenticated public header.
import base64
# Import hashing for canonical release, artifact, and target identities.
import hashlib
# Import keyed hashing for tamper-evident operator-supplied evidence.
import hmac
# Import JSON for deterministic evidence serialization.
import json
# Import environment and fsync support for secret-safe child processes and durable staging.
import os
# Import portable paths for operator-owned programs and encrypted staging only.
from pathlib import Path
# Import regular expressions for strict public digest and version fields.
import re
# Import operating-system randomness for a fresh nonce per encrypted artifact.
import secrets
# Import binary packing for a bounded self-describing header length.
import struct
# Import subprocess support for argv-only logical dump and restore clients.
import subprocess
# Import secure temporary-file creation for encrypted local staging.
import tempfile
# Import daemon watchdog timers for whole-stream child timeouts.
import threading
# Import immutable dataclass support for validated evidence records.
from dataclasses import dataclass
from typing import Any, Mapping

# Identify provider evidence without naming a provider, account, or backup object.
PROVIDER_EVIDENCE_SCHEMA = "casino-provider-backup-evidence-v1"
# Identify one encrypted logical recovery point independently of provider evidence.
RECOVERY_MANIFEST_SCHEMA = "casino-encrypted-recovery-manifest-v1"
# Name the only integrity field added to canonical signed records.
SIGNATURE_FIELD = "evidence_hmac_sha256"
# Accept only complete lowercase SHA-256 values in durable evidence.
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# Accept only the repository's full canonical Git object identity.
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
# Accept legacy three-part and current four-part application versions in recovery evidence.
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:\.\d+)?$")
# Bound provider evidence to one day so cutover cannot rely on an old snapshot.
MAX_PROVIDER_EVIDENCE_AGE_SECONDS = 24 * 60 * 60
# Require at least seven days of destination retention at acknowledgement.
MIN_DESTINATION_RETENTION_SECONDS = 7 * 24 * 60 * 60
# Cap one recovery point at thirty-five days to enforce bounded retention.
MAX_DESTINATION_RETENTION_SECONDS = 35 * 24 * 60 * 60
# Require logical recovery points to be no older than one day at a gate check.
MAX_RECOVERY_POINT_AGE_SECONDS = 24 * 60 * 60
# Identify the authenticated streaming ciphertext format before any parsing.
ENCRYPTED_STREAM_MAGIC = b"VCSREC01"
# Identify the reviewed streaming construction in the signed manifest.
ENCRYPTED_STREAM_SCHEMA = "casino-aes-256-gcm-chunked-v1"
# Use an eight-byte random prefix plus a four-byte monotonic record counter.
GCM_NONCE_PREFIX_BYTES = 8
# Store the standard 128-bit GCM authentication tag at the artifact tail.
GCM_TAG_BYTES = 16
# Bound the authenticated JSON header independently of artifact size.
MAX_HEADER_BYTES = 16 * 1024
# Process logical dumps in bounded memory.
STREAM_CHUNK_BYTES = 64 * 1024
# Encode record type, monotonic index, plaintext length, and ciphertext length.
RECORD_HEADER = struct.Struct(">cIII")


# Surface fixed recovery-policy diagnostics without raw values or exceptions.
class RecoveryError(RuntimeError):
    # Keep one dedicated exception type for CLI and validation fail-closed behavior.
    pass


# Mark an isolated target unusable after any partial restore attempt.
class RecoveryQuarantineRequired(RecoveryError):
    # Keep a distinct type so automation cannot continue toward cutover.
    pass


# Store independent signing material while making formatting intrinsically redacted.
@dataclass(frozen=True, repr=False)
class RecoveryKeys:
    # Store the authenticated-encryption key used only by the later streaming layer.
    encryption_key: bytes
    # Store the evidence-integrity key used only for canonical HMAC records.
    evidence_hmac_key: bytes
    # Store a destination-owned acknowledgement verification key.
    destination_ack_hmac_key: bytes
    # Store a provider-evidence verification key independent of manifest authority.
    provider_evidence_hmac_key: bytes
    # Store an isolated clean-target authorization and result authority.
    restore_evidence_hmac_key: bytes

    # Reject weak or reused keys before any evidence can be trusted.
    def __post_init__(self) -> None:
        # Require a full 256-bit encryption key.
        if len(self.encryption_key) != 32:
            # Stop with a value-free configuration diagnostic.
            raise RecoveryError("Recovery encryption key is invalid")
        # Require at least 256 bits of independently generated HMAC material.
        if len(self.evidence_hmac_key) < 32:
            # Stop with a value-free configuration diagnostic.
            raise RecoveryError("Recovery evidence key is invalid")
        # Require strong destination acknowledgement verification material.
        if len(self.destination_ack_hmac_key) < 32:
            # Reject weak destination authority.
            raise RecoveryError("Destination acknowledgement key is invalid")
        # Require strong provider evidence verification material.
        if len(self.provider_evidence_hmac_key) < 32:
            # Reject weak provider evidence authority.
            raise RecoveryError("Provider evidence key is invalid")
        # Require strong clean-target authorization and result authority.
        if len(self.restore_evidence_hmac_key) < 32:
            # Reject weak restore evidence authority.
            raise RecoveryError("Restore evidence key is invalid")
        # Collect every key role for pairwise independence checks.
        roles = (self.encryption_key, self.evidence_hmac_key, self.destination_ack_hmac_key, self.provider_evidence_hmac_key, self.restore_evidence_hmac_key)
        # Prevent one secret from being reused across any authority roles.
        if any(hmac.compare_digest(left, right) for index, left in enumerate(roles) for right in roles[index + 1:]):
            # Reject any role reuse without formatting secrets.
            raise RecoveryError("Recovery keys must be independent")

    # Return a fixed representation that cannot expose secret bytes.
    def __repr__(self) -> str:
        # Preserve only the record purpose.
        return "<redacted recovery keys>"

    # Reuse the fixed representation for ordinary string conversion.
    def __str__(self) -> str:
        # Return no key material.
        return self.__repr__()


# Store operator-owned process paths and environment under fixed redaction.
@dataclass(frozen=True, repr=False)
class RecoveryProcessConfig:
    # Store one preconfigured no-argument logical dump executable.
    dump_program: Path
    # Store one preconfigured no-argument clean-target restore executable.
    restore_program: Path
    # Store the directory that may contain encrypted staging files only.
    staging_directory: Path
    # Store a child environment that may contain operator-owned secrets.
    process_environment: Mapping[str, str]
    # Bound each logical dump or restore child process.
    timeout_seconds: int = 900

    # Reject ambiguous or unsafe process configuration before child execution.
    def __post_init__(self) -> None:
        # Require absolute program and staging paths without formatting them.
        if not all(path.is_absolute() for path in (self.dump_program, self.restore_program, self.staging_directory)):
            # Reject host-relative resolution.
            raise RecoveryError("Recovery process configuration is invalid")
        # Require a positive bounded timeout and reject booleans.
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, int) or not 1 <= self.timeout_seconds <= 3600:
            # Reject unbounded child execution.
            raise RecoveryError("Recovery process timeout is invalid")
        # Require a plain mapping of text environment names to text values.
        if not isinstance(self.process_environment, Mapping) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in self.process_environment.items()):
            # Reject ambiguous or non-process environment values without formatting them.
            raise RecoveryError("Recovery process environment is invalid")

    # Return a fixed representation that omits paths and environment values.
    def __repr__(self) -> str:
        # Preserve only the configuration purpose.
        return "<redacted recovery process configuration>"

    # Reuse fixed redaction for ordinary string conversion.
    def __str__(self) -> str:
        # Return no path or environment details.
        return self.__repr__()


# Store a completed current provider-backup assertion with no provider identifiers.
@dataclass(frozen=True)
class ProviderBackupEvidence:
    # Record only whether the provider reported completion.
    completed: bool
    # Record when the provider backup completed.
    completed_at: datetime
    # Record when an external read-only verifier observed the provider state.
    verified_at: datetime
    # Record whether the previously approved VM price includes this backup.
    cost_included: bool
    # Bind sanitized evidence content without retaining the signed input object.
    evidence_sha256: str


# Store one encrypted off-instance logical recovery point without destination identifiers.
@dataclass(frozen=True)
class RecoveryManifest:
    # Bind the exact encrypted artifact bytes acknowledged by the destination.
    encrypted_artifact_sha256: str
    # Bind the same exact encrypted bytes with the independent evidence HMAC key.
    encrypted_artifact_hmac_sha256: str
    # Bind the exact encrypted byte length to detect truncation or extension.
    encrypted_size: int
    # Bind the exact logical stream size recorded by the authenticated terminal.
    logical_plaintext_size: int
    # Bind the exact logical stream digest recorded by the authenticated terminal.
    logical_plaintext_sha256: str
    # Bind the reviewed authenticated streaming format.
    encryption_schema: str
    # Bind the exact authenticated header bytes inside the encrypted artifact.
    encryption_header_sha256: str
    # Bind exact ciphertext bytes through a key-independent destination acknowledgement digest.
    destination_ack_sha256: str
    # Bind the immutable application source release.
    release_sha: str
    # Bind the canonical packaged application version.
    app_version: str
    # Bind the independent MySQL migration schema version.
    mysql_schema_version: int
    # Bind the checksum-ordered #204 migration chain.
    migration_chain_sha256: str
    # Bind the source target through keyed opaque evidence rather than an identifier.
    source_target_hmac_sha256: str
    # Record the logical backup completion time.
    completed_at: datetime
    # Record the destination acknowledgement time for the exact encrypted bytes.
    destination_acknowledged_at: datetime
    # Record when the destination retention commitment expires.
    retention_until: datetime
    # Bind the canonical validated manifest without retaining supplied paths or labels.
    evidence_sha256: str


# Store one validated destination acknowledgement without destination identifiers.
@dataclass(frozen=True)
class DestinationAcknowledgement:
    # Bind the exact encrypted artifact bytes.
    encrypted_artifact_sha256: str
    # Bind the exact encrypted byte length.
    encrypted_size: int
    # Record successful durable off-instance acknowledgement.
    acknowledged_at: datetime
    # Record the committed retention boundary.
    retention_until: datetime
    # Bind the canonical signed acknowledgement.
    evidence_sha256: str


# Store clean-target authorization without retaining target identifiers.
@dataclass(frozen=True)
class RestoreAuthorization:
    # Bind the target through an opaque HMAC only.
    target_hmac_sha256: str
    # Bind the exact empty-state proof.
    empty_state_sha256: str
    # Record when isolated target preparation completed.
    prepared_at: datetime
    # Record the short authorization expiry.
    expires_at: datetime
    # Bind the complete signed authorization.
    evidence_sha256: str


# Store post-restore compatibility and recovery timing evidence.
@dataclass(frozen=True)
class RestoreResult:
    # Bind the representative synthetic application state.
    representative_state_sha256: str
    # Bind the #204 structural schema digest.
    schema_state_sha256: str
    # Record observed recovery-point age in seconds.
    observed_rpo_seconds: int
    # Record observed restore duration in seconds.
    observed_rto_seconds: int
    # Bind the complete signed restore result.
    evidence_sha256: str


# Return one UTC-aware timestamp or fail with a fixed diagnostic.
def _parse_time(value: Any, diagnostic: str) -> datetime:
    # Require a string before ISO parsing.
    if not isinstance(value, str):
        # Reject type confusion without echoing content.
        raise RecoveryError(diagnostic)
    # Parse the canonical UTC or offset-aware value under protected error handling.
    try:
        # Normalize the common Z suffix before standard-library parsing.
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # Replace parser details with a secret-safe policy error.
    except (TypeError, ValueError) as exc:
        # Preserve causality without exposing the supplied value.
        raise RecoveryError(diagnostic) from exc
    # Require an explicit timezone to avoid host-local ambiguity.
    if parsed.tzinfo is None:
        # Reject naive timestamps.
        raise RecoveryError(diagnostic)
    # Return one normalized UTC value for comparisons.
    return parsed.astimezone(timezone.utc)


# Serialize a record deterministically after excluding only its signature field.
def canonical_evidence_bytes(record: Mapping[str, Any]) -> bytes:
    # Require a mapping so callers cannot sign ambiguous top-level JSON values.
    if not isinstance(record, Mapping):
        # Reject invalid evidence shapes with a fixed diagnostic.
        raise RecoveryError("Recovery evidence fields are invalid")
    # Remove only the top-level signature while preserving every other field.
    unsigned = {str(key): value for key, value in record.items() if key != SIGNATURE_FIELD}
    # Encode compact sorted ASCII JSON so platforms sign identical bytes.
    try:
        # Return canonical bytes without a trailing newline.
        return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    # Replace unsupported values and recursive structures with a fixed diagnostic.
    except (TypeError, ValueError) as exc:
        # Preserve no supplied value in the raised message.
        raise RecoveryError("Recovery evidence fields are invalid") from exc


# Produce a signed copy for externally stored sanitized evidence.
def sign_evidence(record: Mapping[str, Any], evidence_hmac_key: bytes) -> dict[str, Any]:
    # Require high-entropy evidence signing material.
    if len(evidence_hmac_key) < 32:
        # Reject weak keys without formatting them.
        raise RecoveryError("Recovery evidence key is invalid")
    # Copy the record so the caller's object remains unchanged.
    signed = {str(key): value for key, value in record.items() if key != SIGNATURE_FIELD}
    # Compute an HMAC over every canonical unsigned field.
    signed[SIGNATURE_FIELD] = hmac.new(evidence_hmac_key, canonical_evidence_bytes(signed), hashlib.sha256).hexdigest()
    # Return the independently owned signed record.
    return signed


# Verify a signed record before any semantic field is trusted.
def verify_evidence(record: Mapping[str, Any], evidence_hmac_key: bytes) -> dict[str, Any]:
    # Require high-entropy evidence signing material.
    if len(evidence_hmac_key) < 32:
        # Reject weak keys without formatting them.
        raise RecoveryError("Recovery evidence key is invalid")
    # Read the supplied signature without converting arbitrary objects.
    signature = record.get(SIGNATURE_FIELD) if isinstance(record, Mapping) else None
    # Require the canonical lowercase digest form.
    if not isinstance(signature, str) or not SHA256_RE.fullmatch(signature):
        # Reject unsigned or malformed evidence.
        raise RecoveryError("Recovery evidence integrity is invalid")
    # Compute the expected digest over every unsigned field.
    expected = hmac.new(evidence_hmac_key, canonical_evidence_bytes(record), hashlib.sha256).hexdigest()
    # Compare in constant time to avoid signature oracle behavior.
    if not hmac.compare_digest(signature, expected):
        # Reject any field or signature tampering.
        raise RecoveryError("Recovery evidence integrity is invalid")
    # Return a plain independently owned mapping after integrity verification.
    return {str(key): value for key, value in record.items()}


# Require an exact signed-contract field allowlist after integrity verification.
def _require_signed_fields(record: Mapping[str, Any], fields: set[str], diagnostic: str) -> None:
    # Include only the one canonical signature field beyond semantic fields.
    expected = fields | {SIGNATURE_FIELD}
    # Reject missing or extra fields that could carry private data or ambiguity.
    if set(record) != expected:
        # Surface only the fixed contract diagnostic.
        raise RecoveryError(diagnostic)


# Validate an acknowledgement that is signed and bound to exact encrypted bytes.
def validate_destination_acknowledgement(record: Mapping[str, Any], evidence_hmac_key: bytes, expected_sha256: str, expected_size: int, now: datetime | None = None) -> DestinationAcknowledgement:
    # Verify the complete signed acknowledgement before reading fields.
    verified = verify_evidence(record, evidence_hmac_key)
    # Reject any extra, missing, or private destination evidence fields.
    _require_signed_fields(verified, {"schema", "completed", "durable", "off_instance", "encrypted_artifact_sha256", "encrypted_size", "acknowledged_at", "retention_until"}, "Destination acknowledgement fields are invalid")
    # Require the only reviewed destination acknowledgement contract.
    if verified.get("schema") != "casino-off-instance-destination-ack-v1":
        # Reject another format until reviewed.
        raise RecoveryError("Destination acknowledgement contract is unsupported")
    # Require explicit durable off-instance completion semantics.
    if verified.get("completed") is not True or verified.get("durable") is not True or verified.get("off_instance") is not True:
        # Refuse local staging or partial upload status.
        raise RecoveryError("Destination acknowledgement is incomplete")
    # Validate caller expectations before comparing supplied evidence.
    if not SHA256_RE.fullmatch(expected_sha256) or isinstance(expected_size, bool) or not isinstance(expected_size, int) or expected_size <= 0:
        # Reject malformed internal expectations without echoing them.
        raise RecoveryError("Destination acknowledgement expectation is invalid")
    # Require exact ciphertext checksum and byte-length acknowledgement.
    if verified.get("encrypted_artifact_sha256") != expected_sha256 or verified.get("encrypted_size") != expected_size:
        # Reject acknowledgement of another, partial, or extended object.
        raise RecoveryError("Destination acknowledgement does not match encrypted artifact")
    # Parse the exact acknowledgement time.
    acknowledged_at = _parse_time(verified.get("acknowledged_at"), "Destination acknowledgement timestamps are invalid")
    # Parse the committed retention boundary.
    retention_until = _parse_time(verified.get("retention_until"), "Destination acknowledgement timestamps are invalid")
    # Select a current time without interpreting naive values.
    current_time = now or datetime.now(timezone.utc)
    # Require an explicitly aware decision time.
    if current_time.tzinfo is None:
        # Reject host-local ambiguity.
        raise RecoveryError("Destination acknowledgement timestamps are invalid")
    # Normalize the decision time to UTC.
    current_time = current_time.astimezone(timezone.utc)
    # Require acknowledgement no later than now and active future retention.
    if acknowledged_at > current_time or retention_until <= current_time or retention_until <= acknowledged_at:
        # Refuse future, expired, or contradictory acknowledgement.
        raise RecoveryError("Destination acknowledgement timestamps are invalid")
    # Compute the exact destination retention commitment.
    retention_seconds = (retention_until - acknowledged_at).total_seconds()
    # Enforce the reviewed bounded seven-to-thirty-five-day window.
    if not MIN_DESTINATION_RETENTION_SECONDS <= retention_seconds <= MAX_DESTINATION_RETENTION_SECONDS:
        # Refuse too-short or unbounded retention.
        raise RecoveryError("Destination acknowledgement retention policy is invalid")
    # Hash canonical signed bytes into the manifest's acknowledgement binding.
    evidence_sha256 = hashlib.sha256(canonical_evidence_bytes(verified) + verified[SIGNATURE_FIELD].encode("ascii")).hexdigest()
    # Return sanitized immutable semantics.
    return DestinationAcknowledgement(expected_sha256, expected_size, acknowledged_at, retention_until, evidence_sha256)


# Build the exact authenticated header for one streaming encrypted artifact.
def build_encryption_header(context: Mapping[str, Any], nonce_prefix: bytes) -> bytes:
    # Require the standard fresh per-artifact nonce prefix length.
    if len(nonce_prefix) != GCM_NONCE_PREFIX_BYTES:
        # Reject malformed nonce state before encryption.
        raise RecoveryError("Recovery encryption nonce is invalid")
    # Require a mapping so caller context cannot serialize ambiguously.
    if not isinstance(context, Mapping):
        # Reject invalid authenticated context.
        raise RecoveryError("Recovery encryption context is invalid")
    # Build a public header with no credentials or destination identifiers.
    header = {
        # Identify the reviewed algorithm and framing contract.
        "schema": ENCRYPTED_STREAM_SCHEMA,
        # Encode the random nonce prefix without treating it as a secret.
        "nonce_prefix_b64": base64.b64encode(nonce_prefix).decode("ascii"),
        # Declare the maximum independently authenticated plaintext record size.
        "chunk_size": STREAM_CHUNK_BYTES,
        # Bind only strict-allowlisted release, schema, and opaque-target context.
        "context": validate_backup_context(context),
    }
    # Serialize compact sorted JSON as the exact GCM AAD.
    payload = canonical_evidence_bytes(header)
    # Bound the header before writing or allocating from an untrusted artifact.
    if not payload or len(payload) > MAX_HEADER_BYTES:
        # Reject overlarge authenticated context.
        raise RecoveryError("Recovery encryption header is invalid")
    # Return the exact authenticated JSON bytes.
    return payload


# Write one complete bounded byte sequence or fail before accounting it as emitted.
def _write_exact(target, payload: bytes, diagnostic: str) -> None:
    # Require binary nonempty output controlled by this recovery operation.
    if not isinstance(payload, bytes) or not payload:
        # Reject ambiguous or empty writes without touching the target.
        raise RecoveryError(diagnostic)
    # Write once so any short or zero write is observable and cannot be hidden.
    try:
        # Capture the exact count reported by the binary target.
        written = target.write(payload)
    # Replace pipe, filesystem, and target implementation details.
    except Exception as exc:
        # Surface only the fixed operation-specific diagnostic.
        raise RecoveryError(diagnostic) from exc
    # Require an actual integer equal to the complete authenticated payload length.
    if isinstance(written, bool) or not isinstance(written, int) or written != len(payload):
        # Refuse to hash, count, or continue after partial emission.
        raise RecoveryError(diagnostic)


# Encrypt one logical dump stream directly into an authenticated ciphertext stream.
def encrypt_stream(source, target, encryption_key: bytes, context: Mapping[str, Any]) -> dict[str, Any]:
    # Require an exact AES-256 key before importing the optional crypto backend.
    if len(encryption_key) != 32:
        # Reject invalid key material with a fixed diagnostic.
        raise RecoveryError("Recovery encryption key is invalid")
    # Import the reviewed incremental cipher only when recovery tooling runs.
    try:
        # Import the bounded one-record AES-GCM primitive.
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    # Replace missing or broken optional dependency details with one fixed error.
    except Exception as exc:
        # Stop without falling back to plaintext or unauthenticated encryption.
        raise RecoveryError("Recovery encryption backend is unavailable") from exc
    # Generate a fresh random nonce prefix for every artifact.
    nonce_prefix = secrets.token_bytes(GCM_NONCE_PREFIX_BYTES)
    # Build the exact public authenticated header.
    header = build_encryption_header(context, nonce_prefix)
    # Prefix the format marker and bounded header length before the header.
    prefix = ENCRYPTED_STREAM_MAGIC + struct.pack(">I", len(header)) + header
    # Create the bounded per-record AES-256-GCM primitive.
    cipher = AESGCM(encryption_key)
    # Seed an ordering chain from the exact authenticated artifact header.
    chain = hashlib.sha256(prefix).digest()
    # Initialize bounded plaintext accounting.
    plaintext_size = 0
    # Initialize a digest for representative restore binding without storing plaintext.
    plaintext_digest = hashlib.sha256()
    # Initialize the monotonic authenticated record index.
    chunk_index = 0
    # Write only public framing and authenticated ciphertext records to the target.
    _write_exact(target, prefix, "Encrypted recovery staging write failed")
    # Read the logical dump in bounded chunks until EOF.
    while True:
        # Read no more than the fixed memory bound.
        chunk = source.read(STREAM_CHUNK_BYTES)
        # Stop only on true EOF.
        if not chunk:
            # Leave the bounded streaming loop.
            break
        # Require binary input from the logical dump process.
        if not isinstance(chunk, bytes):
            # Refuse implicit text encoding that could alter restore bytes.
            raise RecoveryError("Logical backup stream is invalid")
        # Refuse counter exhaustion before nonce reuse could occur.
        if chunk_index >= 0xFFFFFFFF:
            # Stop before encrypting another record.
            raise RecoveryError("Logical backup stream is too large")
        # Account for exact plaintext bytes.
        plaintext_size += len(chunk)
        # Hash plaintext only in memory for post-restore equivalence evidence.
        plaintext_digest.update(chunk)
        # Encode this record's exact expected lengths.
        record_header = RECORD_HEADER.pack(b"D", chunk_index, len(chunk), len(chunk) + GCM_TAG_BYTES)
        # Derive a unique 96-bit nonce from random prefix plus monotonic counter.
        nonce = nonce_prefix + struct.pack(">I", chunk_index)
        # Bind header, record identity, lengths, and prior ordering chain as AAD.
        aad = prefix + record_header + chain
        # Encrypt and authenticate this one bounded chunk before writing it.
        ciphertext = cipher.encrypt(nonce, chunk, aad)
        # Write the public record header.
        _write_exact(target, record_header, "Encrypted recovery staging write failed")
        # Write the independently authenticated ciphertext and tag.
        _write_exact(target, ciphertext, "Encrypted recovery staging write failed")
        # Advance the ordering chain over exact stored record bytes.
        chain = hashlib.sha256(chain + record_header + ciphertext).digest()
        # Advance the monotonic nonce and record index.
        chunk_index += 1
    # Reject an empty successful dump before creating a usable recovery point.
    if plaintext_size <= 0:
        # Refuse an empty artifact.
        raise RecoveryError("Logical backup stream is empty")
    # Build an authenticated terminal record binding order, count, size, and digest.
    terminal = json.dumps({"total_chunks": chunk_index, "plaintext_size": plaintext_size, "plaintext_sha256": plaintext_digest.hexdigest(), "chain_sha256": chain.hex()}, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    # Encode the terminal record's exact expected lengths.
    terminal_header = RECORD_HEADER.pack(b"T", chunk_index, len(terminal), len(terminal) + GCM_TAG_BYTES)
    # Derive the next unique nonce for the terminal record.
    terminal_nonce = nonce_prefix + struct.pack(">I", chunk_index)
    # Bind the terminal role, totals, and complete preceding chain as AAD.
    terminal_aad = prefix + terminal_header + chain
    # Encrypt and authenticate the terminal content as one bounded record.
    terminal_ciphertext = cipher.encrypt(terminal_nonce, terminal, terminal_aad)
    # Write the terminal record only after all data records succeed.
    _write_exact(target, terminal_header, "Encrypted recovery staging write failed")
    # Write the authenticated terminal content and tag.
    _write_exact(target, terminal_ciphertext, "Encrypted recovery staging write failed")
    # Return only non-secret deterministic artifact metadata.
    return {
        # Identify the exact framing/algorithm contract.
        "encryption_schema": ENCRYPTED_STREAM_SCHEMA,
        # Bind exact authenticated header bytes.
        "encryption_header_sha256": hashlib.sha256(header).hexdigest(),
        # Record exact plaintext length for restore verification.
        "plaintext_size": plaintext_size,
        # Bind exact logical dump content without retaining it.
        "plaintext_sha256": plaintext_digest.hexdigest(),
    }


# Parse one encrypted stream header and validate its framing without decrypting.
def read_encryption_header(source) -> tuple[bytes, dict[str, Any], bytes, int]:
    # Read the complete fixed framing prefix.
    framing = source.read(len(ENCRYPTED_STREAM_MAGIC) + 4)
    # Require exact magic and header-length bytes.
    if len(framing) != len(ENCRYPTED_STREAM_MAGIC) + 4 or not framing.startswith(ENCRYPTED_STREAM_MAGIC):
        # Reject another, truncated, or plaintext format.
        raise RecoveryError("Encrypted recovery artifact format is invalid")
    # Decode the unsigned bounded header length.
    header_size = struct.unpack(">I", framing[-4:])[0]
    # Require a nonempty bounded authenticated header.
    if header_size <= 0 or header_size > MAX_HEADER_BYTES:
        # Reject malformed framing before allocation.
        raise RecoveryError("Encrypted recovery artifact format is invalid")
    # Read the exact authenticated header bytes.
    header = source.read(header_size)
    # Reject truncated header content.
    if len(header) != header_size:
        # Refuse partial artifacts.
        raise RecoveryError("Encrypted recovery artifact format is invalid")
    # Parse header JSON under fixed diagnostics.
    try:
        # Decode the canonical public header object.
        parsed = json.loads(header.decode("utf-8"))
    # Replace parser details with one secret-safe error.
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        # Refuse malformed header bytes.
        raise RecoveryError("Encrypted recovery artifact format is invalid") from exc
    # Require exactly the reviewed public header keys and chunk bound.
    if not isinstance(parsed, dict) or set(parsed) != {"schema", "nonce_prefix_b64", "chunk_size", "context"} or parsed.get("schema") != ENCRYPTED_STREAM_SCHEMA or parsed.get("chunk_size") != STREAM_CHUNK_BYTES or not isinstance(parsed.get("context"), dict):
        # Reject another format or ambiguous context.
        raise RecoveryError("Encrypted recovery artifact format is invalid")
    # Decode the nonce under fixed diagnostics.
    try:
        # Require canonical base64 without ignored characters.
        nonce_prefix = base64.b64decode(str(parsed.get("nonce_prefix_b64", "")), validate=True)
    # Replace decoding details with one fixed error.
    except (ValueError, TypeError) as exc:
        # Refuse malformed nonce metadata.
        raise RecoveryError("Encrypted recovery artifact format is invalid") from exc
    # Require the standard random nonce-prefix length.
    if len(nonce_prefix) != GCM_NONCE_PREFIX_BYTES:
        # Reject unsupported nonce state.
        raise RecoveryError("Encrypted recovery artifact format is invalid")
    # Strictly validate authenticated context types and reject any extra fields.
    validate_backup_context(parsed["context"])
    # Reconstruct the exact AAD prefix.
    prefix = framing + header
    # Return exact bytes, parsed context, nonce, and ciphertext offset.
    return prefix, parsed, nonce_prefix, len(prefix)


# Compute exact encrypted artifact identity while retaining no bytes in memory.
def encrypted_artifact_identity(source, evidence_hmac_key: bytes) -> tuple[str, str, int]:
    # Require a strong evidence key for a keyed exact-byte binding.
    if len(evidence_hmac_key) < 32:
        # Reject invalid signing material.
        raise RecoveryError("Recovery evidence key is invalid")
    # Rewind a seekable encrypted staging stream.
    try:
        # Start from the first artifact byte.
        source.seek(0)
    # Replace private-path or stream implementation errors.
    except Exception as exc:
        # Require a seekable encrypted artifact.
        raise RecoveryError("Encrypted recovery artifact is unavailable") from exc
    # Initialize a public SHA-256 digest.
    public_digest = hashlib.sha256()
    # Initialize an independent keyed exact-byte digest.
    keyed_digest = hmac.new(evidence_hmac_key, digestmod=hashlib.sha256)
    # Initialize exact byte accounting.
    size = 0
    # Read encrypted bytes in bounded chunks.
    while True:
        # Read no more than the fixed memory bound.
        chunk = source.read(STREAM_CHUNK_BYTES)
        # Stop at true EOF.
        if not chunk:
            # Leave the bounded loop.
            break
        # Require binary artifact content.
        if not isinstance(chunk, bytes):
            # Refuse implicit conversion.
            raise RecoveryError("Encrypted recovery artifact is invalid")
        # Update the public digest.
        public_digest.update(chunk)
        # Update the keyed exact-byte binding.
        keyed_digest.update(chunk)
        # Account for exact bytes.
        size += len(chunk)
    # Require enough bytes for framing plus a terminal record and authentication tag.
    if size <= len(ENCRYPTED_STREAM_MAGIC) + 4 + RECORD_HEADER.size + GCM_TAG_BYTES:
        # Reject empty or truncated artifacts.
        raise RecoveryError("Encrypted recovery artifact is invalid")
    # Rewind for header parsing or authenticated verification.
    source.seek(0)
    # Return both identities and exact length.
    return public_digest.hexdigest(), keyed_digest.hexdigest(), size


# Authenticate and inspect an encrypted stream without releasing plaintext.
def _process_authenticated_records(source, target, encryption_key: bytes, expected_size: int, expected_header_sha256: str, expected_context: Mapping[str, Any]) -> dict[str, Any]:
    # Require an exact AES-256 key.
    if len(encryption_key) != 32:
        # Reject invalid key material.
        raise RecoveryError("Recovery encryption key is invalid")
    # Parse exact authenticated framing and strict public context.
    prefix, parsed, nonce_prefix, _records_offset = read_encryption_header(source)
    # Extract exact header bytes after the fixed framing.
    header = prefix[len(ENCRYPTED_STREAM_MAGIC) + 4:]
    # Require the signed exact header checksum.
    if hashlib.sha256(header).hexdigest() != expected_header_sha256:
        # Reject substituted framing.
        raise RecoveryError("Encrypted recovery artifact header does not match manifest")
    # Require exact allowlisted release/schema/target context.
    if parsed["context"] != validate_backup_context(expected_context):
        # Reject wrong-context restoration.
        raise RecoveryError("Encrypted recovery artifact context does not match manifest")
    # Import the bounded per-record AES-GCM primitive.
    try:
        # Import AESGCM only when recovery tooling runs.
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    # Replace backend details with a fixed error.
    except Exception as exc:
        # Stop without unauthenticated fallback.
        raise RecoveryError("Recovery encryption backend is unavailable") from exc
    # Create the bounded record cipher.
    cipher = AESGCM(encryption_key)
    # Seed exact ordering from authenticated framing.
    chain = hashlib.sha256(prefix).digest()
    # Initialize strict contiguous index.
    expected_index = 0
    # Initialize representative plaintext accounting.
    plaintext_size = 0
    # Initialize representative plaintext digest.
    plaintext_digest = hashlib.sha256()
    # Process independently authenticated records until one terminal record.
    while True:
        # Read one complete public record header.
        record_header = source.read(RECORD_HEADER.size)
        # Reject missing or truncated terminal state.
        if len(record_header) != RECORD_HEADER.size:
            # Refuse incomplete artifacts.
            raise RecoveryError("Encrypted recovery artifact is truncated")
        # Decode record role, index, and lengths.
        record_type, record_index, plaintext_length, ciphertext_length = RECORD_HEADER.unpack(record_header)
        # Require exact monotonic ordering and one standard tag length.
        if record_index != expected_index or ciphertext_length != plaintext_length + GCM_TAG_BYTES:
            # Refuse gaps, reordering, or malformed lengths.
            raise RecoveryError("Encrypted recovery artifact record is invalid")
        # Require bounded data or terminal plaintext.
        if record_type == b"D" and not 1 <= plaintext_length <= STREAM_CHUNK_BYTES:
            # Refuse empty or overlarge data records.
            raise RecoveryError("Encrypted recovery artifact record is invalid")
        # Bound terminal metadata independently of data chunks.
        if record_type == b"T" and not 1 <= plaintext_length <= 4096:
            # Refuse empty or overlarge terminal metadata.
            raise RecoveryError("Encrypted recovery artifact record is invalid")
        # Reject unknown record roles.
        if record_type not in {b"D", b"T"}:
            # Refuse extensibility without review.
            raise RecoveryError("Encrypted recovery artifact record is invalid")
        # Read the complete bounded ciphertext and tag.
        ciphertext = source.read(ciphertext_length)
        # Reject partial record content.
        if len(ciphertext) != ciphertext_length:
            # Refuse truncation before any bytes from this record are released.
            raise RecoveryError("Encrypted recovery artifact is truncated")
        # Derive this record's unique nonce.
        nonce = nonce_prefix + struct.pack(">I", record_index)
        # Bind exact framing, record identity, lengths, and prior chain.
        aad = prefix + record_header + chain
        # Authenticate the complete bounded record before obtaining plaintext.
        try:
            # Return plaintext only after AES-GCM tag verification succeeds.
            plaintext = cipher.decrypt(nonce, ciphertext, aad)
        # Replace cryptographic details with one fixed refusal.
        except Exception as exc:
            # Guarantee no bytes from the modified record reach the target.
            raise RecoveryError("Encrypted recovery artifact authentication failed") from exc
        # Process ordinary authenticated data records.
        if record_type == b"D":
            # Release only this fully authenticated bounded chunk to the restore client.
            if target is not None:
                # Write no unauthenticated bytes.
                _write_exact(target, plaintext, "Clean-target restore write failed")
            # Update representative digest after authentication.
            plaintext_digest.update(plaintext)
            # Update exact plaintext size after authentication.
            plaintext_size += len(plaintext)
            # Advance the exact stored-record ordering chain.
            chain = hashlib.sha256(chain + record_header + ciphertext).digest()
            # Advance the contiguous record index.
            expected_index += 1
            # Continue until the authenticated terminal record.
            continue
        # Decode terminal metadata only after its tag verifies.
        try:
            # Parse the compact ASCII terminal object.
            terminal = json.loads(plaintext.decode("ascii"))
        # Replace parser details with one fixed error.
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            # Refuse malformed authenticated terminal metadata.
            raise RecoveryError("Encrypted recovery artifact terminal is invalid") from exc
        # Require exactly the complete terminal identity fields.
        if not isinstance(terminal, dict) or set(terminal) != {"total_chunks", "plaintext_size", "plaintext_sha256", "chain_sha256"}:
            # Refuse ambiguous or extended terminal records.
            raise RecoveryError("Encrypted recovery artifact terminal is invalid")
        # Require exact count, size, digest, and preceding-chain bindings.
        if terminal.get("total_chunks") != expected_index or terminal.get("plaintext_size") != plaintext_size or terminal.get("plaintext_sha256") != plaintext_digest.hexdigest() or terminal.get("chain_sha256") != chain.hex():
            # Refuse deletion, duplication, or reordering despite per-record tags.
            raise RecoveryError("Encrypted recovery artifact terminal does not match records")
        # Require terminal record to be the exact end of the artifact.
        if source.read(1) != b"":
            # Refuse appended records or hidden bytes.
            raise RecoveryError("Encrypted recovery artifact has trailing content")
        # Require exact total size from the signed manifest.
        if source.tell() != expected_size:
            # Refuse inconsistent stream accounting.
            raise RecoveryError("Encrypted recovery artifact size is invalid")
        # Return only sanitized representative content evidence.
        return {"plaintext_size": plaintext_size, "plaintext_sha256": plaintext_digest.hexdigest(), "context": dict(parsed["context"]), "total_chunks": expected_index}


# Authenticate and inspect every chunk without releasing plaintext.
def verify_encrypted_stream(source, encryption_key: bytes, evidence_hmac_key: bytes, expected_sha256: str, expected_hmac_sha256: str, expected_size: int, expected_header_sha256: str, expected_context: Mapping[str, Any]) -> dict[str, Any]:
    # Require canonical expected identities before reading the artifact.
    if not all(SHA256_RE.fullmatch(value) for value in (expected_sha256, expected_hmac_sha256, expected_header_sha256)) or isinstance(expected_size, bool) or not isinstance(expected_size, int) or expected_size <= 0:
        # Reject malformed internal expectations.
        raise RecoveryError("Encrypted recovery artifact expectation is invalid")
    # Compute exact encrypted identities before record processing.
    actual_sha256, actual_hmac_sha256, actual_size = encrypted_artifact_identity(source, evidence_hmac_key)
    # Require checksum, keyed binding, and length to match the signed manifest.
    if (actual_sha256, actual_hmac_sha256, actual_size) != (expected_sha256, expected_hmac_sha256, expected_size):
        # Refuse changed, substituted, partial, or extended artifacts.
        raise RecoveryError("Encrypted recovery artifact does not match manifest")
    # Process every independently authenticated record without an output target.
    result = _process_authenticated_records(source, None, encryption_key, expected_size, expected_header_sha256, expected_context)
    # Rewind for an optional later restore pass.
    source.seek(0)
    # Return representative verified content identity.
    return result


# Stream only independently authenticated plaintext chunks to a clean-target client.
def decrypt_verified_stream(source, target, encryption_key: bytes, evidence_hmac_key: bytes, expected_sha256: str, expected_hmac_sha256: str, expected_size: int, expected_header_sha256: str, expected_context: Mapping[str, Any]) -> dict[str, Any]:
    # Recompute exact whole-artifact identities immediately before restore.
    actual_sha256, actual_hmac_sha256, actual_size = encrypted_artifact_identity(source, evidence_hmac_key)
    # Require exact manifest bindings after any prior verification pass.
    if (actual_sha256, actual_hmac_sha256, actual_size) != (expected_sha256, expected_hmac_sha256, expected_size):
        # Refuse mutation before starting the target process stream.
        raise RecoveryError("Encrypted recovery artifact does not match manifest")
    # Authenticate each bounded chunk completely before writing that chunk.
    result = _process_authenticated_records(source, target, encryption_key, expected_size, expected_header_sha256, expected_context)
    # Rewind the encrypted staging stream after completion.
    source.seek(0)
    # Return representative restore-stream evidence.
    return result


# Validate current completed provider evidence supplied by an external read-only verifier.
def validate_provider_evidence(record: Mapping[str, Any], evidence_hmac_key: bytes, now: datetime | None = None, max_age_seconds: int = MAX_PROVIDER_EVIDENCE_AGE_SECONDS) -> ProviderBackupEvidence:
    # Verify the complete signed record before reading semantic fields.
    verified = verify_evidence(record, evidence_hmac_key)
    # Reject any extra, missing, or private provider evidence fields.
    _require_signed_fields(verified, {"schema", "completed", "completed_at", "verified_at", "cost_included"}, "Provider backup evidence fields are invalid")
    # Require the only supported provider evidence contract.
    if verified.get("schema") != PROVIDER_EVIDENCE_SCHEMA:
        # Reject another or future format until reviewed.
        raise RecoveryError("Provider backup evidence contract is unsupported")
    # Require explicit completion and inclusion in the already approved cost.
    if verified.get("completed") is not True or verified.get("cost_included") is not True:
        # Refuse partial status snapshots.
        raise RecoveryError("Provider backup evidence is incomplete")
    # Parse the provider-reported completion time.
    completed_at = _parse_time(verified.get("completed_at"), "Provider backup evidence timestamps are invalid")
    # Parse the external read-only observation time.
    verified_at = _parse_time(verified.get("verified_at"), "Provider backup evidence timestamps are invalid")
    # Select the caller-supplied decision time or the current UTC time.
    current_time = now or datetime.now(timezone.utc)
    # Reject a naive caller time rather than interpreting it in a host-local zone.
    if current_time.tzinfo is None:
        # Preserve deterministic UTC-only freshness semantics.
        raise RecoveryError("Provider backup evidence timestamps are invalid")
    # Normalize an explicitly aware caller time to UTC.
    current_time = current_time.astimezone(timezone.utc)
    # Require a positive policy bound no longer than the repository maximum.
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int) or max_age_seconds <= 0 or max_age_seconds > MAX_PROVIDER_EVIDENCE_AGE_SECONDS:
        # Reject weakened or nonsensical freshness policy.
        raise RecoveryError("Provider backup evidence age policy is invalid")
    # Require completion no later than verification and verification no later than now.
    if not completed_at <= verified_at <= current_time:
        # Refuse future or contradictory evidence.
        raise RecoveryError("Provider backup evidence timestamps are invalid")
    # Refuse a stale read-only observation or stale completed backup.
    if (current_time - verified_at).total_seconds() > max_age_seconds or (current_time - completed_at).total_seconds() > max_age_seconds:
        # Keep cutover blocked until current evidence is supplied.
        raise RecoveryError("Provider backup evidence is stale")
    # Hash canonical signed bytes into an opaque evidence identity.
    evidence_sha256 = hashlib.sha256(canonical_evidence_bytes(verified) + verified[SIGNATURE_FIELD].encode("ascii")).hexdigest()
    # Return only sanitized verified semantics.
    return ProviderBackupEvidence(True, completed_at, verified_at, bool(verified["cost_included"]), evidence_sha256)


# Validate one signed encrypted recovery manifest before restore planning.
def validate_recovery_manifest(record: Mapping[str, Any], evidence_hmac_key: bytes, destination_ack_record: Mapping[str, Any], destination_ack_hmac_key: bytes, now: datetime | None = None) -> RecoveryManifest:
    # Verify the complete signed record before reading semantic fields.
    verified = verify_evidence(record, evidence_hmac_key)
    # Reject any extra, missing, or private manifest fields.
    _require_signed_fields(verified, {"schema", "encrypted_artifact_sha256", "encrypted_artifact_hmac_sha256", "encrypted_size", "logical_plaintext_size", "logical_plaintext_sha256", "encryption_schema", "encryption_header_sha256", "destination_ack_sha256", "release_sha", "app_version", "mysql_schema_version", "migration_chain_sha256", "source_target_hmac_sha256", "completed_at", "destination_acknowledged_at", "retention_until"}, "Recovery manifest fields are invalid")
    # Require the only supported logical-recovery manifest contract.
    if verified.get("schema") != RECOVERY_MANIFEST_SCHEMA:
        # Reject another or future format until reviewed.
        raise RecoveryError("Recovery manifest contract is unsupported")
    # Read all SHA-256 fields under one strict canonical rule.
    digest_fields = ("encrypted_artifact_sha256", "encrypted_artifact_hmac_sha256", "logical_plaintext_sha256", "encryption_header_sha256", "destination_ack_sha256", "migration_chain_sha256", "source_target_hmac_sha256")
    # Require every digest to be present and exact.
    if any(not isinstance(verified.get(field), str) or not SHA256_RE.fullmatch(str(verified.get(field))) for field in digest_fields):
        # Reject missing, malformed, or shortened identities.
        raise RecoveryError("Recovery manifest fields are invalid")
    # Require the repository's exact full Git SHA independently of SHA-256 fields.
    if not isinstance(verified.get("release_sha"), str) or not COMMIT_RE.fullmatch(str(verified.get("release_sha"))):
        # Reject shortened, padded, or substituted release provenance.
        raise RecoveryError("Recovery manifest fields are invalid")
    # Require the reviewed authenticated streaming format explicitly.
    if verified.get("encryption_schema") != ENCRYPTED_STREAM_SCHEMA:
        # Reject another cipher or framing contract.
        raise RecoveryError("Recovery manifest encryption format is unsupported")
    # Require canonical application version metadata.
    if not isinstance(verified.get("app_version"), str) or not VERSION_RE.fullmatch(str(verified.get("app_version"))):
        # Reject a manifest that cannot bind release provenance.
        raise RecoveryError("Recovery manifest fields are invalid")
    # Parse positive integer size and schema values without coercing booleans.
    encrypted_size = verified.get("encrypted_size")
    # Read exact logical plaintext length from the authenticated terminal evidence.
    logical_plaintext_size = verified.get("logical_plaintext_size")
    # Read the independent MySQL schema version.
    schema_version = verified.get("mysql_schema_version")
    # Require actual integers and nonempty encrypted content.
    if isinstance(encrypted_size, bool) or not isinstance(encrypted_size, int) or encrypted_size <= 0 or isinstance(logical_plaintext_size, bool) or not isinstance(logical_plaintext_size, int) or logical_plaintext_size <= 0 or isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version <= 0:
        # Reject truncated or unversioned recovery points.
        raise RecoveryError("Recovery manifest fields are invalid")
    # Enforce the exact packaged #204 schema contract for check as well as restore.
    validate_backup_context({
        # Bind the immutable release identity already validated above.
        "release_sha": verified["release_sha"],
        # Bind the canonical packaged application version.
        "app_version": verified["app_version"],
        # Require the manifest's schema version to equal the packaged migration tail.
        "mysql_schema_version": schema_version,
        # Require the manifest's migration chain to equal the packaged immutable chain.
        "migration_chain_sha256": verified["migration_chain_sha256"],
        # Preserve only the manifest's opaque source-target binding.
        "source_target_hmac_sha256": verified["source_target_hmac_sha256"],
    })
    # Parse logical-backup completion time.
    completed_at = _parse_time(verified.get("completed_at"), "Recovery manifest timestamps are invalid")
    # Parse destination acknowledgement time.
    acknowledged_at = _parse_time(verified.get("destination_acknowledged_at"), "Recovery manifest timestamps are invalid")
    # Parse the destination retention boundary.
    retention_until = _parse_time(verified.get("retention_until"), "Recovery manifest timestamps are invalid")
    # Require destination acknowledgement after encrypted artifact completion.
    if acknowledged_at < completed_at or retention_until <= acknowledged_at:
        # Reject contradictory transfer evidence.
        raise RecoveryError("Recovery manifest timestamps are invalid")
    # Verify the destination-owned acknowledgement against exact ciphertext bytes.
    acknowledgement = validate_destination_acknowledgement(destination_ack_record, destination_ack_hmac_key, str(verified["encrypted_artifact_sha256"]), encrypted_size, now)
    # Require the manifest to bind the exact complete signed acknowledgement.
    if verified.get("destination_ack_sha256") != acknowledgement.evidence_sha256:
        # Refuse a free-standing or substituted acknowledgement digest.
        raise RecoveryError("Recovery manifest destination acknowledgement is invalid")
    # Require manifest timestamps and retention to be copied from signed destination evidence.
    if acknowledged_at != acknowledgement.acknowledged_at or retention_until != acknowledgement.retention_until:
        # Refuse source-authored acknowledgement semantics.
        raise RecoveryError("Recovery manifest destination acknowledgement is invalid")
    # Hash canonical signed bytes into an opaque evidence identity.
    evidence_sha256 = hashlib.sha256(canonical_evidence_bytes(verified) + verified[SIGNATURE_FIELD].encode("ascii")).hexdigest()
    # Return immutable validated recovery semantics.
    return RecoveryManifest(str(verified["encrypted_artifact_sha256"]), str(verified["encrypted_artifact_hmac_sha256"]), encrypted_size, logical_plaintext_size, str(verified["logical_plaintext_sha256"]), str(verified["encryption_schema"]), str(verified["encryption_header_sha256"]), str(verified["destination_ack_sha256"]), str(verified["release_sha"]), str(verified["app_version"]), schema_version, str(verified["migration_chain_sha256"]), str(verified["source_target_hmac_sha256"]), completed_at, acknowledged_at, retention_until, evidence_sha256)


# Validate a signed empty-target authorization before any restore child starts.
def validate_restore_authorization(record: Mapping[str, Any], evidence_hmac_key: bytes, expected_target_hmac_sha256: str, now: datetime | None = None) -> RestoreAuthorization:
    # Verify the complete signed authorization first.
    verified = verify_evidence(record, evidence_hmac_key)
    # Reject any extra, missing, or private authorization fields.
    _require_signed_fields(verified, {"schema", "target_hmac_sha256", "clean_target", "empty_target", "disposable", "ambient_target", "existing_table_count", "empty_state_sha256", "prepared_at", "expires_at"}, "Clean-target authorization fields are invalid")
    # Require the only reviewed clean-target contract.
    if verified.get("schema") != "casino-clean-restore-authorization-v1":
        # Reject another format until reviewed.
        raise RecoveryError("Clean-target authorization contract is unsupported")
    # Require a canonical opaque expected target binding.
    if not SHA256_RE.fullmatch(expected_target_hmac_sha256):
        # Reject malformed internal expectations.
        raise RecoveryError("Clean-target expectation is invalid")
    # Require exact target binding plus explicit empty, isolated, disposable semantics.
    if verified.get("target_hmac_sha256") != expected_target_hmac_sha256 or verified.get("clean_target") is not True or verified.get("empty_target") is not True or verified.get("disposable") is not True or verified.get("ambient_target") is not False:
        # Refuse an ambient, existing, nonempty, or wrong target.
        raise RecoveryError("Clean-target authorization is invalid")
    # Require zero observed tables before restore.
    if verified.get("existing_table_count") != 0:
        # Refuse any preexisting schema state without dropping or overwriting it.
        raise RecoveryError("Clean-target authorization is invalid")
    # Require one exact opaque empty-state digest.
    empty_state_sha256 = verified.get("empty_state_sha256")
    # Validate the empty-state digest shape.
    if not isinstance(empty_state_sha256, str) or not SHA256_RE.fullmatch(empty_state_sha256):
        # Reject incomplete pre-restore evidence.
        raise RecoveryError("Clean-target authorization is invalid")
    # Parse the target preparation time.
    prepared_at = _parse_time(verified.get("prepared_at"), "Clean-target authorization timestamps are invalid")
    # Parse the short authorization expiry.
    expires_at = _parse_time(verified.get("expires_at"), "Clean-target authorization timestamps are invalid")
    # Select the current decision time without local-zone interpretation.
    current_time = now or datetime.now(timezone.utc)
    # Require an aware decision time.
    if current_time.tzinfo is None:
        # Reject ambiguous host-local time.
        raise RecoveryError("Clean-target authorization timestamps are invalid")
    # Normalize explicitly aware time to UTC.
    current_time = current_time.astimezone(timezone.utc)
    # Require current short-lived authorization no longer than one hour.
    if not prepared_at <= current_time <= expires_at or (expires_at - prepared_at).total_seconds() > 60 * 60:
        # Refuse stale, future, or overlong authorization.
        raise RecoveryError("Clean-target authorization is stale")
    # Hash exact signed authorization bytes for post-restore binding.
    evidence_sha256 = hashlib.sha256(canonical_evidence_bytes(verified) + verified[SIGNATURE_FIELD].encode("ascii")).hexdigest()
    # Return immutable sanitized authorization semantics.
    return RestoreAuthorization(expected_target_hmac_sha256, empty_state_sha256, prepared_at, expires_at, evidence_sha256)


# Validate #204 schema compatibility and representative state after clean restore.
def validate_restore_result(record: Mapping[str, Any], evidence_hmac_key: bytes, manifest: RecoveryManifest, authorization: RestoreAuthorization, now: datetime | None = None) -> RestoreResult:
    # Verify the complete signed result before reading fields.
    verified = verify_evidence(record, evidence_hmac_key)
    # Reject any extra, missing, or private result fields.
    _require_signed_fields(verified, {"schema", "restore_completed", "schema_compatible", "representative_state_compatible", "encrypted_artifact_sha256", "target_hmac_sha256", "authorization_sha256", "release_sha", "app_version", "mysql_schema_version", "migration_chain_sha256", "schema_state_sha256", "representative_state_sha256", "restore_started_at", "restore_completed_at"}, "Clean-target restore result fields are invalid")
    # Require the only reviewed restore-result contract.
    if verified.get("schema") != "casino-clean-restore-result-v1":
        # Reject another result format until reviewed.
        raise RecoveryError("Clean-target restore result contract is unsupported")
    # Require explicit successful compatibility semantics.
    if verified.get("restore_completed") is not True or verified.get("schema_compatible") is not True or verified.get("representative_state_compatible") is not True:
        # Keep cutover blocked on any failed verification.
        raise RecoveryError("Clean-target restore verification failed")
    # Bind exact artifact, target, authorization, release, and #204 schema identities.
    bindings = {
        # Bind the encrypted recovery point.
        "encrypted_artifact_sha256": manifest.encrypted_artifact_sha256,
        # Bind the isolated restore target.
        "target_hmac_sha256": authorization.target_hmac_sha256,
        # Bind the exact empty-target authorization.
        "authorization_sha256": authorization.evidence_sha256,
        # Bind the immutable application release.
        "release_sha": manifest.release_sha,
        # Bind the canonical application version.
        "app_version": manifest.app_version,
        # Bind the independent MySQL migration version.
        "mysql_schema_version": manifest.mysql_schema_version,
        # Bind the exact #204 migration chain.
        "migration_chain_sha256": manifest.migration_chain_sha256,
    }
    # Require every signed binding to match the accepted manifest and authorization.
    if any(verified.get(field) != value for field, value in bindings.items()):
        # Refuse wrong-artifact, wrong-target, wrong-release, or wrong-schema evidence.
        raise RecoveryError("Clean-target restore result does not match recovery point")
    # Read the structural and representative state digests.
    digest_fields = ("schema_state_sha256", "representative_state_sha256")
    # Require exact public SHA-256 identities.
    if any(not isinstance(verified.get(field), str) or not SHA256_RE.fullmatch(str(verified.get(field))) for field in digest_fields):
        # Reject incomplete compatibility evidence.
        raise RecoveryError("Clean-target restore result fields are invalid")
    # Parse signed restore start time.
    restore_started_at = _parse_time(verified.get("restore_started_at"), "Clean-target restore timing evidence is invalid")
    # Parse signed restore completion time.
    restore_completed_at = _parse_time(verified.get("restore_completed_at"), "Clean-target restore timing evidence is invalid")
    # Select an explicitly aware verification time.
    current_time = now or datetime.now(timezone.utc)
    # Reject host-local ambiguity.
    if current_time.tzinfo is None:
        # Preserve UTC-only timing policy.
        raise RecoveryError("Clean-target restore timing evidence is invalid")
    # Normalize the decision time to UTC.
    current_time = current_time.astimezone(timezone.utc)
    # Require backup completion, restore start, restore completion, and verification ordering.
    if not manifest.completed_at <= restore_started_at <= restore_completed_at <= current_time:
        # Reject caller-invented or future timing.
        raise RecoveryError("Clean-target restore timing evidence is invalid")
    # Recompute RPO from recovery-point completion to restore start.
    rpo = int((restore_started_at - manifest.completed_at).total_seconds())
    # Recompute RTO from signed restore start to completion.
    rto = int((restore_completed_at - restore_started_at).total_seconds())
    # Bound both observations to seven days so stale drills cannot satisfy cutover.
    if rpo > 7 * 24 * 60 * 60 or rto > 7 * 24 * 60 * 60:
        # Refuse stale recovery timing evidence.
        raise RecoveryError("Clean-target restore timing evidence is stale")
    # Hash exact signed result bytes for durable handoff.
    evidence_sha256 = hashlib.sha256(canonical_evidence_bytes(verified) + verified[SIGNATURE_FIELD].encode("ascii")).hexdigest()
    # Return only sanitized compatibility and timing evidence.
    return RestoreResult(str(verified["representative_state_sha256"]), str(verified["schema_state_sha256"]), rpo, rto, evidence_sha256)


# Validate the sanitized release/schema/target context embedded as GCM AAD.
def validate_backup_context(context: Mapping[str, Any]) -> dict[str, Any]:
    # Require exactly the reviewed public context keys.
    expected_keys = {"release_sha", "app_version", "mysql_schema_version", "migration_chain_sha256", "source_target_hmac_sha256"}
    # Reject extra or missing fields that could carry identifiers or drift.
    if not isinstance(context, Mapping) or set(context) != expected_keys:
        # Keep authenticated context minimal and sanitized.
        raise RecoveryError("Recovery encryption context is invalid")
    # Require a full canonical Git SHA and semantic application version.
    if not COMMIT_RE.fullmatch(str(context.get("release_sha", ""))) or not VERSION_RE.fullmatch(str(context.get("app_version", ""))):
        # Reject unbound release provenance.
        raise RecoveryError("Recovery encryption context is invalid")
    # Require a positive independent MySQL schema version.
    schema_version = context.get("mysql_schema_version")
    # Reject booleans and invalid versions.
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version <= 0:
        # Refuse unversioned schema evidence.
        raise RecoveryError("Recovery encryption context is invalid")
    # Require canonical migration and opaque target HMAC bindings.
    if not SHA256_RE.fullmatch(str(context.get("migration_chain_sha256", ""))) or not SHA256_RE.fullmatch(str(context.get("source_target_hmac_sha256", ""))):
        # Refuse malformed #204 or target provenance.
        raise RecoveryError("Recovery encryption context is invalid")
    # Import the #204 checksum-bound schema contract only when recovery tooling runs.
    try:
        # Load the exact catalog and prefix-digest helper without opening a database.
        from casino.core.mysql_migrations import load_catalog, migration_chain_digest
        # Read the local immutable migration contract.
        migrations, expected_version, minimum_version, _ = load_catalog()
    # Replace catalog, path, and parser details with one fixed error.
    except Exception as exc:
        # Refuse recovery when packaged migration provenance cannot be verified.
        raise RecoveryError("Recovery MySQL schema contract is unavailable") from exc
    # Require one runtime-compatible version and its exact applied migration prefix.
    if schema_version < minimum_version or schema_version > expected_version or context.get("migration_chain_sha256") != migration_chain_digest(migrations, schema_version):
        # Refuse a recovery point for another version or migration prefix.
        raise RecoveryError("Recovery encryption context does not match packaged MySQL schema")
    # Return one plain sanitized copy.
    return {str(key): value for key, value in context.items()}


# Format one aware UTC timestamp canonically for signed evidence.
def _format_time(value: datetime) -> str:
    # Require timezone-aware input.
    if value.tzinfo is None:
        # Reject host-local ambiguity.
        raise RecoveryError("Recovery timestamp is invalid")
    # Normalize to UTC and use the explicit Z suffix.
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# Remove only an encrypted staging file created by this recovery operation.
def _remove_created_staging(path: Path) -> None:
    # Ignore a missing already-cleaned staging file.
    try:
        # Delete exactly the known temporary file without recursion.
        path.unlink(missing_ok=True)
    # Replace host/path details with a fixed policy failure.
    except OSError as exc:
        # Surface cleanup failure because retained staging needs operator action.
        raise RecoveryError("Encrypted staging cleanup failed") from exc


# Start a daemon watchdog that bounds stream reads as well as process wait.
def _start_process_watchdog(process, timeout_seconds: int) -> tuple[threading.Event, threading.Timer]:
    # Create a durable timeout flag shared with the pipeline thread.
    timed_out = threading.Event()

    # Kill only the tracked child when the whole-operation deadline expires.
    def expire() -> None:
        # Mark timeout before signaling the process.
        timed_out.set()
        # Avoid signaling a process that already exited.
        if process.poll() is None:
            # Kill only this tracked wrapper process.
            process.kill()

    # Create one daemon timer so it cannot keep interpreter shutdown alive.
    timer = threading.Timer(timeout_seconds, expire)
    # Mark the watchdog as a daemon helper.
    timer.daemon = True
    # Start whole-operation timing immediately after child creation.
    timer.start()
    # Return both observable timeout state and cancellation handle.
    return timed_out, timer


# Run the no-argument logical dump client and create encrypted staging only.
def create_encrypted_staging(config: RecoveryProcessConfig, keys: RecoveryKeys, context: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    # Validate exact sanitized AAD context before creating any file or process.
    validated_context = validate_backup_context(context)
    # Require an existing operator-owned staging directory and never create it implicitly.
    if not config.staging_directory.is_dir():
        # Stop before process execution without exposing the path.
        raise RecoveryError("Encrypted staging directory is unavailable")
    # Create one exclusive encrypted temporary file under the operator-selected directory.
    staging_handle = tempfile.NamedTemporaryFile(mode="w+b", prefix=".casino-recovery-", suffix=".enc", dir=config.staging_directory, delete=False)
    # Retain the exact created path only for controlled staging operations.
    staging_path = Path(staging_handle.name)
    # Track a child only after successful creation.
    process = None
    # Track the whole-stream watchdog only after child creation.
    watchdog = None
    # Track whether the whole operation exceeded its deadline.
    timed_out = None
    # Start protected pipeline execution and encrypted-file handling.
    try:
        # Spawn the preconfigured wrapper with no arguments and no shell interpolation.
        process = subprocess.Popen([str(config.dump_program)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=False, env=dict(config.process_environment), close_fds=True)
        # Bound stdout reads and process completion under one deadline.
        timed_out, watchdog = _start_process_watchdog(process, config.timeout_seconds)
        # Require the binary stdout pipe created above.
        if process.stdout is None:
            # Refuse an unusable child boundary.
            raise RecoveryError("Logical backup process failed")
        # Stream logical bytes directly from child stdout into AES-GCM ciphertext.
        encryption = encrypt_stream(process.stdout, staging_handle, keys.encryption_key, validated_context)
        # Close the parent read handle so the child can terminate cleanly.
        process.stdout.close()
        # Wait for the dump wrapper under the configured bound.
        return_code = process.wait(timeout=config.timeout_seconds)
        # Stop the watchdog after complete stream drain and process exit.
        watchdog.cancel()
        # Refuse output from a child killed by the whole-operation deadline.
        if timed_out.is_set():
            # Treat even a zero-looking post-kill status as timeout failure.
            raise RecoveryError("Logical backup process timed out")
        # Reject any nonzero child after draining the complete stream.
        if return_code != 0:
            # Refuse partial output even when it encrypted successfully.
            raise RecoveryError("Logical backup process failed")
        # Flush ciphertext through Python buffering.
        staging_handle.flush()
        # Flush ciphertext through the operating-system file cache.
        os.fsync(staging_handle.fileno())
        # Rewind for exact identity computation.
        staging_handle.seek(0)
        # Compute public checksum, keyed exact-byte binding, and length.
        artifact_sha256, artifact_hmac_sha256, artifact_size = encrypted_artifact_identity(staging_handle, keys.evidence_hmac_key)
        # Add exact artifact identities to the returned sanitized metadata.
        encryption.update({"encrypted_artifact_sha256": artifact_sha256, "encrypted_artifact_hmac_sha256": artifact_hmac_sha256, "encrypted_size": artifact_size})
        # Close the staging handle before destination transfer.
        staging_handle.close()
        # Return the encrypted staging path plus sanitized metadata.
        return staging_path, encryption
    # Convert child timeouts into one fixed failure.
    except subprocess.TimeoutExpired as exc:
        # Kill only the tracked child process created above.
        if process is not None:
            # Terminate the timed-out synthetic or operator-owned wrapper.
            process.kill()
            # Reap it so no child remains.
            process.wait()
        # Cancel any redundant watchdog callback.
        if watchdog is not None:
            # Prevent a later callback after cleanup.
            watchdog.cancel()
        # Close the staging handle before removing partial ciphertext.
        staging_handle.close()
        # Remove only this operation's partial encrypted staging file.
        _remove_created_staging(staging_path)
        # Surface no program path or process output.
        raise RecoveryError("Logical backup process timed out") from exc
    # Convert all other pipeline failures while preserving fixed policy errors.
    except Exception as exc:
        # Cancel the watchdog on every non-timeout exit path.
        if watchdog is not None:
            # Prevent a later callback after cleanup.
            watchdog.cancel()
        # Kill a still-running tracked child only.
        if process is not None and process.poll() is None:
            # Terminate the failed pipeline child.
            process.kill()
            # Reap it without exposing output.
            process.wait()
        # Close the staging handle if it remains open.
        if not staging_handle.closed:
            # Release the encrypted file handle.
            staging_handle.close()
        # Remove partial ciphertext because no destination acknowledgement can exist.
        _remove_created_staging(staging_path)
        # Preserve already fixed policy diagnostics.
        if isinstance(exc, RecoveryError):
            # Re-raise the fixed diagnostic.
            raise
        # Replace process, path, and operating-system details.
        raise RecoveryError("Logical backup pipeline failed") from exc


# Transfer encrypted staging, commit signed metadata, then remove local staging.
def complete_off_instance_backup(config: RecoveryProcessConfig, keys: RecoveryKeys, context: Mapping[str, Any], destination, now: datetime | None = None) -> dict[str, Any]:
    # Reject an ambiguous injected decision time before starting the operation.
    if now is not None and now.tzinfo is None:
        # Reject ambiguous host-local time.
        raise RecoveryError("Recovery timestamp is invalid")
    # Create only encrypted local staging from the no-argument dump client.
    staging_path, metadata = create_encrypted_staging(config, keys, context)
    # Record completion only after the logical dump and durable ciphertext flush.
    completed_at = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)
    # Retain encrypted staging on destination or manifest failure for operator retry/quarantine.
    try:
        # Ask the preconfigured destination adapter to upload exact encrypted bytes.
        acknowledgement_record = destination.upload_artifact(staging_path, metadata["encrypted_artifact_sha256"], metadata["encrypted_artifact_hmac_sha256"], metadata["encrypted_size"])
        # Validate signed durable off-instance acknowledgement of exact ciphertext.
        acknowledgement = validate_destination_acknowledgement(acknowledgement_record, keys.destination_ack_hmac_key, metadata["encrypted_artifact_sha256"], metadata["encrypted_size"], now or datetime.now(timezone.utc))
        # Copy the already validated AAD context.
        validated_context = validate_backup_context(context)
        # Assemble the complete signed recovery manifest.
        manifest = sign_evidence({
            # Identify the reviewed recovery manifest.
            "schema": RECOVERY_MANIFEST_SCHEMA,
            # Bind exact ciphertext checksum.
            "encrypted_artifact_sha256": metadata["encrypted_artifact_sha256"],
            # Bind exact ciphertext through the independent evidence key.
            "encrypted_artifact_hmac_sha256": metadata["encrypted_artifact_hmac_sha256"],
            # Bind exact ciphertext length.
            "encrypted_size": metadata["encrypted_size"],
            # Bind exact logical stream length from the authenticated terminal.
            "logical_plaintext_size": metadata["plaintext_size"],
            # Bind exact logical stream digest from the authenticated terminal.
            "logical_plaintext_sha256": metadata["plaintext_sha256"],
            # Bind the reviewed algorithm and framing contract.
            "encryption_schema": metadata["encryption_schema"],
            # Bind exact authenticated header bytes.
            "encryption_header_sha256": metadata["encryption_header_sha256"],
            # Bind the complete signed destination acknowledgement.
            "destination_ack_sha256": acknowledgement.evidence_sha256,
            # Bind immutable release provenance.
            "release_sha": validated_context["release_sha"],
            # Bind canonical application version.
            "app_version": validated_context["app_version"],
            # Bind independent #204 schema version.
            "mysql_schema_version": validated_context["mysql_schema_version"],
            # Bind exact #204 migration chain.
            "migration_chain_sha256": validated_context["migration_chain_sha256"],
            # Bind the source target without exposing its identifier.
            "source_target_hmac_sha256": validated_context["source_target_hmac_sha256"],
            # Record logical backup completion.
            "completed_at": _format_time(completed_at),
            # Record exact destination acknowledgement time.
            "destination_acknowledged_at": _format_time(acknowledgement.acknowledged_at),
            # Record destination retention commitment.
            "retention_until": _format_time(acknowledgement.retention_until),
        }, keys.evidence_hmac_key)
        # Validate the assembled manifest before committing it.
        validated_manifest = validate_recovery_manifest(manifest, keys.evidence_hmac_key, acknowledgement_record, keys.destination_ack_hmac_key, now or datetime.now(timezone.utc))
        # Serialize canonical signed manifest bytes for destination storage.
        manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        # Bind exact signed manifest bytes independently of destination implementation.
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        # Commit the manifest only after ciphertext acknowledgement.
        manifest_ack_record = destination.commit_manifest(manifest_bytes, manifest_sha256, validated_manifest.encrypted_artifact_sha256)
        # Verify the complete signed manifest acknowledgement.
        manifest_ack = verify_evidence(manifest_ack_record, keys.destination_ack_hmac_key)
        # Reject any extra, missing, or private manifest acknowledgement fields.
        _require_signed_fields(manifest_ack, {"schema", "completed", "durable", "off_instance", "manifest_sha256", "encrypted_artifact_sha256"}, "Destination manifest acknowledgement fields are invalid")
        # Require exact durable manifest and artifact bindings.
        if manifest_ack.get("schema") != "casino-off-instance-manifest-ack-v1" or manifest_ack.get("completed") is not True or manifest_ack.get("durable") is not True or manifest_ack.get("off_instance") is not True or manifest_ack.get("manifest_sha256") != manifest_sha256 or manifest_ack.get("encrypted_artifact_sha256") != validated_manifest.encrypted_artifact_sha256:
            # Retain encrypted staging until a valid metadata acknowledgement exists.
            raise RecoveryError("Destination manifest acknowledgement is invalid")
        # Remove local encrypted staging only after both destination acknowledgements.
        _remove_created_staging(staging_path)
        # Return the complete signed manifest to the operator for external evidence storage.
        return manifest
    # Preserve encrypted staging on any destination-side or acknowledgement failure.
    except Exception as exc:
        # Preserve fixed recovery diagnostics unchanged.
        if isinstance(exc, RecoveryError):
            # Re-raise without path or adapter details.
            raise
        # Replace adapter-specific identifiers and exceptions.
        raise RecoveryError("Off-instance backup acknowledgement failed; encrypted staging retained") from exc


# Enforce recovery-point age and active retention before restore or cutover.
def validate_recovery_age(manifest: RecoveryManifest, now: datetime | None = None, max_age_seconds: int = MAX_RECOVERY_POINT_AGE_SECONDS) -> dict[str, int]:
    # Select an explicitly aware gate decision time.
    current_time = now or datetime.now(timezone.utc)
    # Reject host-local ambiguity.
    if current_time.tzinfo is None:
        # Preserve UTC-only recovery age policy.
        raise RecoveryError("Recovery age decision time is invalid")
    # Normalize explicitly aware time to UTC.
    current_time = current_time.astimezone(timezone.utc)
    # Require a positive integer bound no greater than the repository maximum.
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int) or not 1 <= max_age_seconds <= MAX_RECOVERY_POINT_AGE_SECONDS:
        # Reject weakened or ambiguous monitoring policy.
        raise RecoveryError("Recovery age policy is invalid")
    # Require the recovery point to predate the gate decision.
    if manifest.completed_at > current_time:
        # Reject future recovery points.
        raise RecoveryError("Recovery point timestamp is invalid")
    # Compute exact recovery-point age.
    age_seconds = int((current_time - manifest.completed_at).total_seconds())
    # Keep the gate blocked when age exceeds the explicit RPO alert threshold.
    if age_seconds > max_age_seconds:
        # Require a new completed off-instance recovery point.
        raise RecoveryError("Recovery point age alert is active")
    # Require destination retention to remain active at the gate decision.
    if manifest.retention_until <= current_time:
        # Refuse an expired destination object.
        raise RecoveryError("Recovery point retention alert is active")
    # Compute remaining committed retention.
    retention_remaining_seconds = int((manifest.retention_until - current_time).total_seconds())
    # Return only sanitized monitoring values.
    return {"age_seconds": age_seconds, "retention_remaining_seconds": retention_remaining_seconds}


# Download exact encrypted bytes into isolated encrypted staging only.
def download_encrypted_staging(config: RecoveryProcessConfig, keys: RecoveryKeys, manifest: RecoveryManifest, destination, now: datetime | None = None, started_at: datetime | None = None) -> Path:
    # Select the signed receipt's earliest acceptable completion time.
    download_started_at = started_at or now or datetime.now(timezone.utc)
    # Reject host-local ambiguity before creating encrypted staging.
    if download_started_at.tzinfo is None:
        # Preserve UTC-only receipt ordering.
        raise RecoveryError("Destination download receipt timestamps are invalid")
    # Normalize the operation start to UTC.
    download_started_at = download_started_at.astimezone(timezone.utc)
    # Require an existing operator-owned staging directory and never create it implicitly.
    if not config.staging_directory.is_dir():
        # Stop without exposing the path.
        raise RecoveryError("Encrypted staging directory is unavailable")
    # Create one exclusive encrypted download file.
    staging_handle = tempfile.NamedTemporaryFile(mode="w+b", prefix=".casino-restore-", suffix=".enc", dir=config.staging_directory, delete=False)
    # Retain the exact created path only for controlled staging operations.
    staging_path = Path(staging_handle.name)
    # Start protected destination download handling.
    try:
        # Ask the preconfigured adapter to stream exact encrypted bytes into staging.
        receipt_record = destination.download_artifact(staging_handle, manifest.encrypted_artifact_sha256, manifest.encrypted_size)
        # Flush downloaded ciphertext through Python buffering.
        staging_handle.flush()
        # Flush downloaded ciphertext through the operating-system file cache.
        os.fsync(staging_handle.fileno())
        # Close the staging handle before independent verification.
        staging_handle.close()
        # Verify the destination-owned download receipt.
        receipt = verify_evidence(receipt_record, keys.destination_ack_hmac_key)
        # Reject any extra, missing, or private download receipt fields.
        _require_signed_fields(receipt, {"schema", "completed", "durable", "off_instance", "encrypted_artifact_sha256", "encrypted_size", "downloaded_at"}, "Destination download receipt fields are invalid")
        # Require exact successful off-instance download semantics.
        if receipt.get("schema") != "casino-off-instance-download-receipt-v1" or receipt.get("completed") is not True or receipt.get("durable") is not True or receipt.get("off_instance") is not True or receipt.get("encrypted_artifact_sha256") != manifest.encrypted_artifact_sha256 or receipt.get("encrypted_size") != manifest.encrypted_size:
            # Refuse partial, local, or wrong-object downloads.
            raise RecoveryError("Destination download receipt is invalid")
        # Parse the signed download completion time.
        downloaded_at = _parse_time(receipt.get("downloaded_at"), "Destination download receipt timestamps are invalid")
        # Select the aware decision time.
        current_time = now or datetime.now(timezone.utc)
        # Reject host-local ambiguity before comparing signed receipt ordering.
        if current_time.tzinfo is None:
            # Refuse an ambiguous validation boundary.
            raise RecoveryError("Destination download receipt timestamps are invalid")
        # Normalize the post-download validation time to UTC.
        current_time = current_time.astimezone(timezone.utc)
        # Require receipt completion during this exact download operation.
        if not download_started_at <= downloaded_at <= current_time:
            # Refuse stale replay or future receipt timing.
            raise RecoveryError("Destination download receipt timestamps are invalid")
        # Return only the created encrypted staging path.
        return staging_path
    # Remove partial downloads because the durable off-instance source remains authoritative.
    except Exception as exc:
        # Close the staging handle if still open.
        if not staging_handle.closed:
            # Release the partial encrypted file.
            staging_handle.close()
        # Remove only this operation's created encrypted download staging.
        _remove_created_staging(staging_path)
        # Preserve fixed policy diagnostics.
        if isinstance(exc, RecoveryError):
            # Re-raise the fixed diagnostic.
            raise
        # Replace destination and path details.
        raise RecoveryError("Off-instance recovery download failed") from exc


# Restore authenticated logical bytes only into a separately authorized empty target.
def restore_clean_target(config: RecoveryProcessConfig, keys: RecoveryKeys, manifest_record: Mapping[str, Any], destination_ack_record: Mapping[str, Any], authorization_record: Mapping[str, Any], expected_target_hmac_sha256: str, destination, expected_context: Mapping[str, Any], post_restore_verifier, now: datetime | None = None) -> RestoreResult:
    # Select an explicitly aware decision time.
    decision_time = now or datetime.now(timezone.utc)
    # Reject host-local ambiguity.
    if decision_time.tzinfo is None:
        # Stop before download or process execution.
        raise RecoveryError("Recovery timestamp is invalid")
    # Normalize the decision time to UTC.
    decision_time = decision_time.astimezone(timezone.utc)
    # Validate the source manifest paired with exact destination-owned acknowledgement.
    manifest = validate_recovery_manifest(manifest_record, keys.evidence_hmac_key, destination_ack_record, keys.destination_ack_hmac_key, decision_time)
    # Enforce current recovery-point and active-retention monitoring.
    validate_recovery_age(manifest, decision_time)
    # Validate the independently authorized empty isolated target.
    authorization = validate_restore_authorization(authorization_record, keys.restore_evidence_hmac_key, expected_target_hmac_sha256, decision_time)
    # Require exact authenticated context to match manifest provenance.
    validated_context = validate_backup_context(expected_context)
    # Compare every authenticated context field with the signed manifest.
    if validated_context != {"release_sha": manifest.release_sha, "app_version": manifest.app_version, "mysql_schema_version": manifest.mysql_schema_version, "migration_chain_sha256": manifest.migration_chain_sha256, "source_target_hmac_sha256": manifest.source_target_hmac_sha256}:
        # Refuse wrong-release or wrong-schema restore configuration.
        raise RecoveryError("Recovery context does not match manifest")
    # Preserve deterministic tests only when an explicit decision time was supplied.
    receipt_validation_time = now
    # Download exact encrypted bytes while bounding its receipt from preflight through post-download validation.
    staging_path = download_encrypted_staging(config, keys, manifest, destination, receipt_validation_time, decision_time)
    # Track the restore child only after successful creation.
    process = None
    # Track the whole-stream watchdog after child creation.
    watchdog = None
    # Track whole-operation timeout state.
    timed_out = None
    # Start protected preverification, restore, and compatibility validation.
    try:
        # Open encrypted staging read-only for no-output preverification.
        with staging_path.open("rb") as encrypted_source:
            # Authenticate the whole artifact and terminal without starting a restore child.
            verified_stream = verify_encrypted_stream(encrypted_source, keys.encryption_key, keys.evidence_hmac_key, manifest.encrypted_artifact_sha256, manifest.encrypted_artifact_hmac_sha256, manifest.encrypted_size, manifest.encryption_header_sha256, validated_context)
            # Require terminal plaintext identity to match signed manifest metadata.
            if verified_stream.get("plaintext_size") != manifest.logical_plaintext_size or verified_stream.get("plaintext_sha256") != manifest.logical_plaintext_sha256:
                # Refuse a coherently framed but wrong logical recovery point.
                raise RecoveryError("Encrypted recovery logical content does not match manifest")
            # Spawn the preconfigured no-argument clean-target wrapper only after full preverification.
            process = subprocess.Popen([str(config.restore_program)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False, env=dict(config.process_environment), close_fds=True)
            # Require the binary stdin pipe created above.
            if process.stdin is None:
                # Refuse an unusable child boundary.
                raise RecoveryQuarantineRequired("Clean-target restore failed; target quarantine is required")
            # Bound authenticated streaming and process completion under one deadline.
            timed_out, watchdog = _start_process_watchdog(process, config.timeout_seconds)
            # Stream only independently authenticated chunks into restore stdin.
            restored_stream = decrypt_verified_stream(encrypted_source, process.stdin, keys.encryption_key, keys.evidence_hmac_key, manifest.encrypted_artifact_sha256, manifest.encrypted_artifact_hmac_sha256, manifest.encrypted_size, manifest.encryption_header_sha256, validated_context)
            # Close stdin so the wrapper can finish applying the authenticated logical stream.
            process.stdin.close()
            # Wait under the same watchdog deadline.
            return_code = process.wait(timeout=config.timeout_seconds)
            # Stop the watchdog after process exit.
            watchdog.cancel()
            # Require timeout-free zero exit and exact terminal content identity.
            if timed_out.is_set() or return_code != 0 or restored_stream.get("plaintext_size") != manifest.logical_plaintext_size or restored_stream.get("plaintext_sha256") != manifest.logical_plaintext_sha256:
                # Mark the isolated target unusable for cutover.
                raise RecoveryQuarantineRequired("Clean-target restore failed; target quarantine is required")
        # Ask the independent verifier for signed #204 schema and representative-state evidence.
        result_record = post_restore_verifier(manifest, authorization)
        # Validate exact bindings and recompute RPO/RTO from signed timestamps.
        result = validate_restore_result(result_record, keys.restore_evidence_hmac_key, manifest, authorization, now or datetime.now(timezone.utc))
        # Remove downloaded encrypted staging only after complete compatibility proof.
        _remove_created_staging(staging_path)
        # Return sanitized restore timing and compatibility evidence.
        return result
    # Convert timeout, decrypt, process, and terminal failures into mandatory quarantine.
    except Exception as exc:
        # Cancel a pending watchdog before child cleanup.
        if watchdog is not None:
            # Prevent a later callback after cleanup.
            watchdog.cancel()
        # Kill only a still-running tracked restore wrapper.
        if process is not None and process.poll() is None:
            # Terminate the partial clean-target restore process.
            process.kill()
        # Reap the tracked wrapper without exposing its output.
        if process is not None:
            # Wait for process cleanup under a short fixed bound.
            try:
                # Reap the known child.
                process.wait(timeout=5)
            # Ignore only reaping details because the quarantine result already blocks cutover.
            except Exception:
                # Preserve the fixed quarantine diagnostic.
                pass
        # Attempt encrypted staging cleanup without replacing the quarantine diagnostic.
        try:
            # Remove only the downloaded encrypted copy; durable destination bytes remain.
            _remove_created_staging(staging_path)
        # Preserve the original fail-closed result even if cleanup needs operator action.
        except RecoveryError:
            # Keep mandatory quarantine as the dominant outcome.
            pass
        # Preserve pre-process policy failures that cannot have mutated the target.
        if process is None and isinstance(exc, RecoveryError):
            # Re-raise the fixed pre-restore diagnostic.
            raise
        # Convert every post-spawn failure into mandatory target quarantine.
        raise RecoveryQuarantineRequired("Clean-target restore failed; target quarantine is required") from exc
