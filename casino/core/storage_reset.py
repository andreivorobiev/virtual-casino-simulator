# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""JSON reset, rollback, and stable-visibility lifecycle for the storage package."""

# Import deep-copy support so immutable game-action history survives reset.
import copy
# Import hashing so rollback restoration verifies exact regular-file bytes.
import hashlib
# Import operating-system primitives for durable artifacts and directory flushes.
import os
# Import filesystem copying and removal for exact reset and rollback behavior.
import shutil
# Import tar archives for one durable private pre-reset snapshot.
import tarfile
# Import context-manager support for reset and stable-visibility boundaries.
from contextlib import contextmanager
# Import path typing for private recovery artifact boundaries.
from pathlib import Path

# Import the fixed public conflict boundary used by reset recovery.
from casino.errors import ConflictError

# Version the provider-private durable action files independently from public storage.
_GAME_ACTION_STORAGE_VERSION = 1
# Version epoch-scoped lifecycle registries without rewriting legacy epoch-one bytes.
_GAME_ACTION_EPOCH_STORAGE_VERSION = 2
# Bound reset epochs to the signed BIGINT range shared by JSON and MySQL providers.
_GAME_ACTION_MAX_EPOCH = (1 << 63) - 1


# Own the JSON reset lifecycle while the concrete provider remains in storage.py.
class JsonResetMixin:
    # Clear JSON data while preserving the held legacy lock file and identity.
    def _reset_locked(self) -> None:
        # Resolve the exact lock entry that must survive reset.
        legacy_lock = self.ledger_lock_path()
        # Enumerate every current data-root child under stable and legacy locks.
        for child in tuple(self.data_dir.iterdir()):
            # Preserve the exact open legacy lock inode across the reset.
            if child == legacy_lock:
                # Continue without unlinking or replacing the interoperability lock.
                continue
            # Remove directories recursively using the existing reset semantics.
            if child.is_dir() and not child.is_symlink():
                # Delete only this exact data-root child tree.
                shutil.rmtree(child)
            # Remove files, symlinks, and other leaf entries without following them.
            else:
                # Delete only this exact data-root child.
                child.unlink()
        # Drop the ledger tail cache so reads never serve pre-reset rows. (issue #412)
        self._drop_ledger_cache()
        # Drop the action-registry cache alongside its removed backing file. (issue #412)
        self._drop_actions_cache()
        # Recreate every ordinary provider directory before caller bootstrap.
        self._ensure_ready_direct()

    # Return the stable prefix shared by this provider's reset recovery artifacts.
    def _reset_backup_prefix(self) -> str:
        # Return a fixed private prefix inside this canonical data root's control directory.
        return "reset-backup-"

    # Return one collision-resistant sibling path for a reset rollback snapshot.
    def _reset_backup_path(self) -> Path:
        # Keep one single-file rollback artifact in the verified private control root.
        return self._json_control_root() / f"{self._reset_backup_prefix()}{os.getpid()}-{os.urandom(8).hex()}.tar"

    # Reject unresolved reset recovery material before exposing provider state.
    def _require_no_reset_recovery_locked(self) -> None:
        try:
            # Resolve the verified private control root without creating any filesystem entry.
            control_root = self._json_control_root()
            # Discover only this canonical provider root's final recovery artifacts.
            backups = tuple(control_root.glob(f"{self._reset_backup_prefix()}*.tar"))
            # Discover only this canonical provider root's unpublished staging artifacts.
            temporaries = tuple(control_root.glob(f"{self._reset_backup_prefix()}*.tar.tmp-*"))
            # Combine the two exact provider-owned residue patterns.
            residues = backups + temporaries
        # Normalize discovery failures without exposing filesystem details.
        except OSError:
            # Require operator recovery when the private recovery boundary cannot be inspected.
            raise ConflictError("JSON reset requires operator recovery") from None
        # Fail closed while any prior reset recovery artifact remains unresolved.
        if residues:
            # Prevent later reads or writes from bypassing a failed reset boundary.
            raise ConflictError("JSON reset requires operator recovery")

    # Validate one private archive member before using its relative path.
    def _reset_archive_member_parts(self, name: str) -> tuple[str, ...]:
        # Reject empty, absolute, backslash, drive-like, and non-canonical archive names.
        if type(name) is not str or not name or name.startswith("/") or "\\" in name or ":" in name:
            # Preserve the private archive for operator recovery.
            raise ConflictError("JSON reset requires operator recovery")
        # Split the provider-created POSIX archive path without filesystem resolution.
        parts = tuple(name.split("/"))
        # Reject traversal, empty segments, and redundant current-directory segments.
        if any(part in {"", ".", ".."} for part in parts):
            # Preserve the private archive for operator recovery.
            raise ConflictError("JSON reset requires operator recovery")
        # Return the exact safe relative path components.
        return parts

    # Return the exact SHA-256 digest of one regular file without exposing its path.
    def _reset_file_digest(self, path: Path) -> str:
        # Initialize one deterministic streaming digest.
        digest = hashlib.sha256()
        try:
            # Open only the validated regular file in binary mode.
            with path.open("rb") as handle:
                # Read bounded chunks until the complete file has been hashed.
                while True:
                    # Read one bounded block without retaining file contents.
                    chunk = handle.read(1024 * 1024)
                    # Stop after the final empty read.
                    if not chunk:
                        # Leave the streaming loop after complete input.
                        break
                    # Incorporate this exact file block into the digest.
                    digest.update(chunk)
        # Normalize file-read failures without exposing private paths.
        except OSError:
            # Preserve the recovery artifact for operator review.
            raise ConflictError("JSON reset requires operator recovery") from None
        # Return the complete lowercase digest.
        return digest.hexdigest()

    # Flush restored directory entries before declaring rollback durable.
    def _fsync_reset_directories_locked(self) -> None:
        # Windows lacks a portable directory-handle fsync boundary.
        if os.name == "nt":
            # Rely on flushed files and atomic namespace operations on Windows.
            return
        # Enumerate deepest directories first, then the provider root itself.
        directories = sorted((entry for entry in self.data_dir.rglob("*") if entry.is_dir()), key=lambda entry: len(entry.parts), reverse=True)
        # Include the provider root whose direct children were restored.
        directories.append(self.data_dir)
        # Include the data-root parent whose child identity must remain durable.
        directories.append(self.data_dir.parent)
        # Flush each exact restored directory entry table.
        for directory in directories:
            # Track the raw descriptor for guaranteed release.
            descriptor = None
            try:
                # Open the exact directory without following a caller-provided path.
                descriptor = os.open(directory, os.O_RDONLY)
                # Flush contained entry names and metadata through the operating system.
                os.fsync(descriptor)
            # Normalize any durability failure into the recovery boundary.
            except OSError:
                # Preserve the sole rollback artifact.
                raise ConflictError("JSON reset requires operator recovery") from None
            finally:
                # Close only a descriptor successfully opened above.
                if descriptor is not None:
                    # Release the directory handle after flush or failure.
                    os.close(descriptor)

    # Copy complete pre-reset bytes into one durable artifact outside the reset root.
    def _create_reset_backup_locked(self) -> Path:
        # Allocate one collision-resistant final rollback path.
        backup = self._reset_backup_path()
        # Allocate one collision-resistant sibling temp used only by this transaction.
        temporary = backup.with_suffix(backup.suffix + f".tmp-{os.urandom(8).hex()}")
        # Track whether atomic publication consumed the temporary path.
        published = False
        try:
            # Resolve the legacy lock entry whose inode stays in place.
            legacy_lock = self.ledger_lock_path()
            # Open the private artifact exclusively so residue can never be overwritten.
            with temporary.open("xb") as raw_handle:
                # Stream one uncompressed archive whose file bytes remain exact.
                with tarfile.open(fileobj=raw_handle, mode="w", dereference=False) as archive:
                    # Walk every provider entry in deterministic relative-path order.
                    entries = sorted(self.data_dir.rglob("*"), key=lambda item: item.relative_to(self.data_dir).as_posix())
                    # Serialize every directory and regular file exactly once.
                    for entry in entries:
                        # Keep the separately preserved legacy lock out of rollback state.
                        if entry == legacy_lock:
                            # Continue because the open lock identity survives reset.
                            continue
                        # Reject links and special entries instead of copying external content.
                        if entry.is_symlink() or (not entry.is_dir() and not entry.is_file()):
                            # Preserve source state and fail before destructive reset.
                            raise ConflictError("JSON reset requires operator recovery")
                        # Derive the exact portable member name beneath the provider root.
                        member_name = entry.relative_to(self.data_dir).as_posix()
                        # Add this single entry without recursive duplicate traversal.
                        archive.add(entry, arcname=member_name, recursive=False)
                # Flush Python buffers after the complete tar stream is finalized.
                raw_handle.flush()
                # Flush exact rollback bytes through the operating system.
                os.fsync(raw_handle.fileno())
            # Publish the complete single-file recovery artifact atomically.
            temporary.replace(backup)
            # Record that the final path now owns the durable recovery bytes.
            published = True
            # Flush the sibling directory entry on platforms that support it.
            self._fsync_game_action_parent(backup)
        # Normalize every staging failure without exposing paths or source names.
        except BaseException:
            try:
                # Remove only an unpublished private temporary artifact.
                temporary.unlink(missing_ok=True)
            # Preserve the fixed recovery boundary even if temp cleanup fails.
            except OSError:
                # Require operator recovery without exposing filesystem details.
                raise ConflictError("JSON reset requires operator recovery") from None
            # Keep any published backup after a durability failure for operator recovery.
            if published:
                # Normalize the failure while retaining the only recovery artifact.
                raise ConflictError("JSON reset requires operator recovery") from None
            # Normalize pre-publication failures while original state remains untouched.
            raise ConflictError("JSON reset backup failed") from None
        # Return the complete durable private rollback artifact.
        return backup

    # Restore complete pre-reset bytes after a failed caller bootstrap.
    def _restore_reset_backup_locked(self, backup: Path) -> None:
        try:
            # Open the single durable rollback artifact without modifying it.
            with tarfile.open(backup, mode="r:") as archive:
                # Read the complete member table before destructive restoration.
                members = archive.getmembers()
                # Reject duplicate or case-colliding durable member identities.
                normalized_names = [os.path.normcase(member.name) for member in members]
                # Require every recorded entry to have one unique platform identity.
                if len(normalized_names) != len(set(normalized_names)):
                    # Preserve the archive and current partial state for operator recovery.
                    raise ConflictError("JSON reset requires operator recovery")
                # Validate every member before clearing partial post-reset state.
                for member in members:
                    # Accept only ordinary directories and regular files.
                    if not member.isdir() and not member.isfile():
                        # Reject links and special archive entries.
                        raise ConflictError("JSON reset requires operator recovery")
                    # Validate the exact relative member path.
                    self._reset_archive_member_parts(member.name)
                # Record the exact expected directory and regular-file inventory.
                expected_inventory = {member.name: "directory" if member.isdir() else "file" for member in members}
                # Record exact file sizes and hashes before destructive restoration.
                expected_files = {}
                # Inspect every regular-file member in the intact archive.
                for member in members:
                    # Skip directory entries because their identity is verified by inventory.
                    if member.isdir():
                        # Continue to the next archive member.
                        continue
                    # Open the archived regular-file payload for pre-restore verification.
                    source = archive.extractfile(member)
                    # Reject a malformed archive missing regular-file bytes.
                    if source is None:
                        # Preserve the archive for operator recovery.
                        raise ConflictError("JSON reset requires operator recovery")
                    # Initialize the member's exact streaming digest.
                    digest = hashlib.sha256()
                    # Track the exact number of bytes read from the archive.
                    byte_count = 0
                    # Consume the member under its archive-owned handle.
                    with source:
                        # Read bounded chunks until the member is complete.
                        while True:
                            # Read one bounded archive block.
                            chunk = source.read(1024 * 1024)
                            # Stop after the final empty read.
                            if not chunk:
                                # Leave the member loop after complete input.
                                break
                            # Add this block to the exact digest.
                            digest.update(chunk)
                            # Add this block length to the exact byte count.
                            byte_count += len(chunk)
                    # Require the physical payload length to match tar metadata.
                    if byte_count != member.size:
                        # Preserve the archive and current state for operator recovery.
                        raise ConflictError("JSON reset requires operator recovery")
                    # Store the exact expected size and digest by safe member name.
                    expected_files[member.name] = (member.size, digest.hexdigest())
                # Remove every partial post-reset entry while preserving the held legacy lock.
                self._reset_locked()
                # Restore directories before their contained regular files.
                for member in sorted(members, key=lambda item: (not item.isdir(), item.name)):
                    # Resolve the validated destination beneath the provider root.
                    destination = self.data_dir.joinpath(*self._reset_archive_member_parts(member.name))
                    # Recreate an exact directory entry when the member is a directory.
                    if member.isdir():
                        # Create parents so nested empty directories are preserved.
                        destination.mkdir(parents=True, exist_ok=True)
                        # Continue to the next archive member after directory creation.
                        continue
                    # Create the validated parent before restoring file bytes.
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    # Open the archived regular-file payload.
                    source = archive.extractfile(member)
                    # Reject a malformed archive missing regular-file bytes.
                    if source is None:
                        # Preserve the archive for operator recovery.
                        raise ConflictError("JSON reset requires operator recovery")
                    # Stream exact original bytes into a newly created destination.
                    with source, destination.open("xb") as target:
                        # Copy without interpreting JSON or changing byte content.
                        shutil.copyfileobj(source, target)
                        # Flush Python buffering before the restored file becomes visible.
                        target.flush()
                        # Flush restored file bytes through the operating system.
                        os.fsync(target.fileno())
            # Allow focused tests to alter restored bytes before durable verification.
            self._reset_recovery_checkpoint("restore_copied")
            # Build the exact restored inventory excluding the separately preserved legacy lock.
            actual_inventory = {}
            # Resolve the exact legacy lock entry excluded from the archive.
            legacy_lock = self.ledger_lock_path()
            # Enumerate every restored provider entry in deterministic order.
            for entry in sorted(self.data_dir.rglob("*"), key=lambda item: item.relative_to(self.data_dir).as_posix()):
                # Exclude only the stable legacy lock preserved across reset.
                if entry == legacy_lock:
                    # Continue without treating the lock as reset state.
                    continue
                # Derive the exact portable relative identity.
                relative_name = entry.relative_to(self.data_dir).as_posix()
                # Reject links and special files introduced during restoration.
                if entry.is_symlink() or (not entry.is_dir() and not entry.is_file()):
                    # Preserve the rollback artifact and fail closed.
                    raise ConflictError("JSON reset requires operator recovery")
                # Record the exact restored entry type.
                actual_inventory[relative_name] = "directory" if entry.is_dir() else "file"
            # Require exact restored names and types before deleting recovery material.
            if actual_inventory != expected_inventory:
                # Preserve the rollback artifact for operator recovery.
                raise ConflictError("JSON reset requires operator recovery")
            # Verify every restored regular file against archive size and digest.
            for relative_name, (expected_size, expected_digest) in expected_files.items():
                # Resolve the already-validated restored path.
                restored_path = self.data_dir.joinpath(*self._reset_archive_member_parts(relative_name))
                try:
                    # Read the exact restored byte length from filesystem metadata.
                    restored_size = restored_path.stat().st_size
                # Normalize stat failures without exposing private paths.
                except OSError:
                    # Preserve the archive for operator recovery.
                    raise ConflictError("JSON reset requires operator recovery") from None
                # Require exact physical byte length and streaming digest.
                if restored_size != expected_size or self._reset_file_digest(restored_path) != expected_digest:
                    # Preserve the archive for operator recovery.
                    raise ConflictError("JSON reset requires operator recovery")
            # Flush restored namespace entries before declaring verification durable.
            self._fsync_reset_directories_locked()
            # Mark exact durable restoration after inventory, byte, and namespace proof.
            self._reset_recovery_checkpoint("restore_verified")
            # Drop caches so later reads observe restored bytes rather than reset state.
            self._drop_ledger_cache()
            # Drop committed-action cache identities tied to removed post-reset files.
            self._drop_actions_cache()
        # Preserve the sole recovery artifact and normalize every restoration failure.
        except (OSError, tarfile.TarError, ConflictError):
            # Hold all later provider visibility at the operator-recovery boundary.
            raise ConflictError("JSON reset requires operator recovery") from None

    # Remove one exact reset rollback artifact after success or restoration.
    def _remove_reset_backup(self, backup: Path) -> None:
        try:
            # Atomically unlink the sole task-owned rollback artifact.
            backup.unlink()
        # Normalize cleanup failures without exposing the host path.
        except OSError:
            # Prevent releasing a reset boundary with silent task residue.
            raise ConflictError("JSON reset cleanup failed") from None

    # Hold reset, recreation, and caller bootstrap under one reentrant provider gate.
    @contextmanager
    def reset_transaction(self):
        # Reject destructive provider mutation from inside a planner.
        self._reject_planner_mutation()
        # Serialize reset and nested bootstrap calls in this process.
        with self.lock:
            # Hold stable then legacy cross-process locks until final visibility.
            with self._json_global_gate():
                # Converge every recoverable action before retiring its mutable epoch.
                self._recover_all_json_actions_locked()
                # Read the exact ready epoch before creating rollback material.
                epoch_state = self._read_game_action_epoch()
                # Refuse nested or stale reset ownership.
                if epoch_state["phase"] != "ready" or epoch_state["current_epoch"] >= _GAME_ACTION_MAX_EPOCH:
                    # Keep every provider byte unchanged at the fixed recovery boundary.
                    raise ConflictError("Game action reset requires operator recovery")
                # Capture the epoch that remains immutable history after this reset.
                current_epoch = epoch_state["current_epoch"]
                # Validate and retain every committed receipt across the reset.
                receipt_registry, _receipts = self._read_game_action_receipts(current_epoch)
                # Validate and retain every execute or uncommitted claim across the reset.
                claim_registry, _claims = self._read_game_action_claims(current_epoch)
                # Convert legacy epoch-one receipts only inside the reset transaction.
                if receipt_registry["schema_version"] == _GAME_ACTION_STORAGE_VERSION:
                    # Preserve each serialized legacy receipt unchanged under epoch one.
                    receipt_registry = {"schema_version": _GAME_ACTION_EPOCH_STORAGE_VERSION, "receipts_by_epoch": {"1": copy.deepcopy(receipt_registry["receipts"])}}
                # Convert legacy epoch-one claims only inside the reset transaction.
                if claim_registry["schema_version"] == _GAME_ACTION_STORAGE_VERSION:
                    # Preserve each serialized legacy claim unchanged under epoch one.
                    claim_registry = {"schema_version": _GAME_ACTION_EPOCH_STORAGE_VERSION, "claims_by_epoch": {"1": copy.deepcopy(claim_registry["claims"])}}
                # Derive the next namespace without permitting wraparound.
                next_epoch = current_epoch + 1
                # Snapshot complete pre-reset bytes before destructive mutation.
                backup = self._create_reset_backup_locked()
                # Capture any reset or caller-body failure without releasing either gate.
                failure = None
                try:
                    # Clear provider state without replacing either lock identity.
                    self._reset_locked()
                    # Restore immutable receipt history after mutable state is cleared.
                    self._write_game_action_json(self.game_action_receipts_path(), receipt_registry)
                    # Restore immutable claim and tombstone history beside receipts.
                    self._write_game_action_json(self.game_action_claims_path(), claim_registry)
                    # Publish the new namespace as unavailable throughout caller bootstrap.
                    self._write_game_action_epoch(current_epoch=next_epoch, phase="resetting")
                    # Yield so app bootstrap writes remain inside the same reentrant boundary.
                    yield self
                    # Release the exact bootstrapped namespace only after the caller body succeeds.
                    self._write_game_action_epoch(current_epoch=next_epoch, phase="ready")
                # Capture clear or bootstrap failure for rollback under the held gate.
                except BaseException as error:
                    # Retain the original failure until restoration and cleanup succeed.
                    failure = error
                # Restore complete pre-reset bytes after clear or caller-body failure.
                if failure is not None:
                    try:
                        # Replace partial post-reset state before releasing visibility.
                        self._restore_reset_backup_locked(backup)
                        # Remove the recovery artifact only after exact restoration.
                        self._remove_reset_backup(backup)
                    # Preserve unresolved recovery material and block later provider entry.
                    except BaseException:
                        # Surface one fixed operator-recovery boundary.
                        raise ConflictError("JSON reset requires operator recovery") from None
                    # Re-raise the original body failure only after exact rollback and cleanup.
                    raise failure
                try:
                    # Commit success by atomically removing the sole recovery artifact.
                    self._remove_reset_backup(backup)
                # Convert cleanup failure into exact rollback before returning an error.
                except BaseException:
                    try:
                        # Restore the complete pre-reset state from the intact artifact.
                        self._restore_reset_backup_locked(backup)
                        # Retry exact artifact deletion after successful restoration.
                        self._remove_reset_backup(backup)
                    # Preserve recovery material and block later visibility on rollback failure.
                    except BaseException:
                        # Surface one fixed operator-recovery boundary.
                        raise ConflictError("JSON reset requires operator recovery") from None
                    # Report cleanup failure only after pre-reset state is restored.
                    raise ConflictError("JSON reset cleanup failed") from None

    # Reset local JSON storage through the complete provider-owned boundary.
    def reset(self) -> None:
        # Hold the reset transaction even when no caller bootstrap follows.
        with self.reset_transaction():
            # Preserve direct reset behavior without additional writes.
            pass

    # Hold one provider-wide visibility boundary for direct JSON tree readers.
    @contextmanager
    def state_visibility_transaction(self):
        # Serialize direct state enumeration with local provider operations.
        with self.lock:
            # Serialize direct state enumeration with reset and independent processes.
            with self._json_global_gate():
                # Converge any pending durable action before exposing provider state.
                self._recover_all_json_actions_locked()
                # Transfer control while the complete JSON tree remains stable.
                yield self
