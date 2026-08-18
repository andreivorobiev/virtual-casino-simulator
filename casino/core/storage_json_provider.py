# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import annotations so provider type hints can refer to classes declared later.
from __future__ import annotations
# Import deep-copy support so indexed reads cannot mutate cached durable events.
import copy
# Import required dependency so decimal balances use one explicit cents rule.
from decimal import Decimal
# Import required dependency so provider payloads can be serialized consistently.
import json
# Import required dependency so environment configuration can select the provider.
import os
# Import required dependency so JSON fallback storage can manage local files.
import shutil
# Import required dependency so JSON fallback writes remain process-thread atomic.
import threading
# Import required dependency so Windows replace retries can wait for transient file-handle release.
import time
# Import required dependency so local JSON fallback paths stay platform-safe.
from pathlib import Path
# Import required dependency so provider methods can accept default factories.
from typing import Any, Callable

# Import the player-document schema version used by ordinary JSON writes.
from casino.config import SCHEMA_VERSION
# Import required dependency so provider-created rows use the app timestamp format.
from casino.core.clock import utc_now
# Import the route-free executor interface required by the provider MRO.
from casino.core.game_action import GameActionExecutor
# Import the provider-neutral contract and exact helpers used by ordinary JSON methods.
from casino.core.storage_base import HISTORY_FIELDS, StorageProvider, _action_details, _action_fingerprint, _action_scope, _ledger_event, _money_decimal, _normalize_action_key, _quantized_money, _quantized_money_decimal, _validate_action_replay, _validate_wallet_normalization_replay, _validated_players_document, _validated_strict_document, _wallet_normalization_event
# Import the bounded JSON reset lifecycle owner.
from casino.core.storage_reset import JsonResetMixin
# Import the bounded JSON game-action lifecycle owner.
from casino.core.storage_game_actions_json import JsonGameActionMixin
# Import the bounded JSON filesystem, locking, cache, and planner substrate.
from casino.core.storage_json_infrastructure import JsonInfrastructureMixin
# Import required dependency so storage providers surface existing API errors.
from casino.errors import ConflictError, InsufficientFundsError, NotFoundError, ValidationError

# Compact the append-only ledger-action journal only after a bounded growth interval. (LEDGER-034)
_LEDGER_ACTION_COMPACT_BYTES = 512 * 1024


# Define the JsonStorageProvider that preserves default local file behavior.
class JsonStorageProvider(JsonInfrastructureMixin, JsonGameActionMixin, JsonResetMixin, StorageProvider, GameActionExecutor):
    # Store the provider name used by diagnostics and tests.
    name = "json"

    # Load players without acquiring another operating-system wallet lock.
    def _load_players_document(self, default_factory: Callable[[], dict]) -> dict:
        # Read the wallet document strictly so corruption never selects bootstrap defaults.
        return self._read_players_document(default_factory)

    # Save players without acquiring another gate or invoking recovery.
    def _save_players_document(self, state: dict) -> None:
        # Copy the state so callers do not observe schema mutation side effects.
        saved_state = dict(state)
        # Preserve the current schema version on every saved player document.
        saved_state["schema_version"] = SCHEMA_VERSION
        # Refuse any internal writer that attempts to publish non-cent wallet state.
        _validated_players_document(saved_state)
        # Write the normalized player document to disk.
        self._write_json(self.players_path(), saved_state)

    # Load players after recovering any committed action projection from a prior process.
    def load_players(self, default_factory: Callable[[], dict]) -> dict:
        # Guard recovery and the player read from concurrent local threads.
        with self.lock:
            # Guard recovery and the player read from independent processes.
            with self._ledger_process_lock():
                # Complete every recoverable wallet action before exposing players.
                self._recover_all_json_actions_locked()
                # Return the compatible player document after recovery.
                return self._load_players_document(default_factory)

    # Scan or repair JSON wallet residue under the complete money-state gate. (STORAGE-015, LEDGER-036)
    def normalize_wallet_balances(self, *, apply: bool = False) -> dict:
        # Reject operator mutation attempted from inside a game-action planner.
        self._reject_planner_mutation()
        # Serialize the scan with every provider-local operation.
        with self.lock:
            # Serialize the pass with reset, wallet, ledger, and game-action writers across processes.
            with self._ledger_process_lock():
                # Converge any earlier durable money action before inspecting its wallet projection.
                self._recover_all_json_actions_locked()
                # Read the structurally strict document through the residue-aware operator boundary.
                state = self._read_normalizable_players_document()
                # Collect exact stored and normalized values without mutating the source yet.
                residues = []
                # Visit every wallet exactly once while the global gate remains held.
                for player in state["players"]:
                    # Decode the exact stored decimal value already accepted by the strict reader.
                    stored = _money_decimal(player["balance"])
                    # Derive the canonical cent value using the documented provider-neutral rule.
                    normalized = _quantized_money_decimal(stored)
                    # Record only values that contain genuine sub-cent residue.
                    if stored != normalized:
                        # Retain the row and exact decimal pair for an optional apply pass.
                        residues.append((player, stored, normalized))
                # Return the read-only scan result without writing players or ledger rows.
                if not apply:
                    # Publish bounded counts only, never player identities or stored values.
                    return {"provider": self.name, "checked": len(state["players"]), "residue_count": len(residues), "normalized_count": 0, "clean": not residues, "applied": False}
                # Refresh the append-only ledger identity cache before deterministic replay checks.
                self._ledger_rows()
                # Publish every required audit row before changing the compatible wallet document.
                for player, stored, normalized in residues:
                    # Build the deterministic ledger-visible operator adjustment.
                    event = _wallet_normalization_event(player["player_id"], stored, normalized)
                    # Reuse an earlier row when a prior process appended it before a stopped player write.
                    existing = self._ledger_cache_by_id.get(event["ledger_id"])
                    # Append only a previously unseen normalization identity.
                    if existing is None:
                        # Write the complete append-only evidence while the process gate is held.
                        self._append_jsonl(self.ledger_path(), event)
                        # Refresh the cache so later rows in this batch see the durable append.
                        self._ledger_rows()
                    else:
                        # Require the earlier deterministic row to describe this exact residue.
                        _validate_wallet_normalization_replay(existing, event)
                    # Replace the durable wallet value only after its audit evidence exists.
                    player["balance"] = _quantized_money(normalized)
                    # Record the operator pass as the latest wallet update.
                    player["updated_at"] = utc_now()
                # Publish the complete normalized player document once after all audit rows are durable.
                if residues:
                    # Use the existing atomic JSON replacement boundary.
                    self._save_players_document(state)
                # Prove the resulting in-memory document satisfies the ordinary exact-cent reader.
                _validated_players_document(state)
                # Return bounded completion evidence for the operator command.
                return {"provider": self.name, "checked": len(state["players"]), "residue_count": len(residues), "normalized_count": len(residues), "clean": True, "applied": True}

    # Insert one player through the deterministic provider-owned identity boundary.
    def insert_player(self, player: dict) -> dict:
        # Reuse the exactly-once insert-or-read semantics already required by invitations.
        return self.ensure_player(player)

    # Insert only missing bootstrap players under one JSON wallet boundary. (STORAGE-012, issue #431)
    def bootstrap_players(self, state: dict) -> None:
        # Reject bootstrap mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Guard the complete bootstrap batch from concurrent local threads.
        with self.lock:
            # Serialize bootstrap with every wallet action across processes.
            with self._json_global_gate():
                # Complete every recoverable action before adding missing wallets.
                self._recover_all_json_actions_locked()
                # Load the current document without inventing unrelated defaults.
                current = self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
                # Index durable identifiers so repeated or racing bootstrap calls are harmless.
                identifiers = {row.get("player_id") for row in current.get("players", []) if isinstance(row, dict)}
                # Track whether this call contributed any previously missing row.
                changed = False
                # Visit each bounded bootstrap row exactly once.
                for player in state.get("players", []):
                    # Ignore an already durable identifier without overwriting wallet or lifecycle fields.
                    if player.get("player_id") in identifiers:
                        # Continue to the remaining default rows.
                        continue
                    # Detach and cents-normalize the missing wallet before publication.
                    inserted = {**player, "balance": _quantized_money(player.get("balance", 0))}
                    # Append the validated row while the cross-process wallet gate remains held.
                    current["players"].append(inserted)
                    # Reserve the identifier against duplicates inside the same supplied batch.
                    identifiers.add(player.get("player_id"))
                    # Record that the normalized document must be published once.
                    changed = True
                # Persist only when at least one missing row was appended.
                if changed:
                    # Publish the complete JSON document atomically under the held wallet boundary.
                    self._save_players_document(current)

    # Update one player with the existing callback semantics.
    def update_player(self, player_id: str, updater: Callable[[dict], None]) -> dict:
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Guard read-modify-write with the provider lock.
        with self.lock:
            # Guard the read-modify-write operation from independent processes.
            with self._ledger_process_lock():
                # Complete every recoverable wallet action before applying a later update.
                self._recover_all_json_actions_locked()
                # Load the current players document using an empty fallback.
                state = self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
                # Iterate through players to find the requested row.
                for player in state["players"]:
                    # Branch when this row matches the requested player ID.
                    if player["player_id"] == player_id:
                        # Let the caller mutate the player copy in place.
                        updater(player)
                        # Quantize every direct wallet update through the canonical cents boundary.
                        player["balance"] = _quantized_money(player.get("balance", 0))
                        # Stamp the update time for downstream admin views.
                        player["updated_at"] = utc_now()
                        # Persist the modified player document.
                        self._save_players_document(state)
                        # Return the updated player row to the caller.
                        return player
        # Raise a consistent not-found error when no player matched.
        raise NotFoundError(f"Player {player_id} was not found")

    # Create one deterministic player under the same cross-process wallet lock used by updates.
    def ensure_player(self, player: dict) -> dict:
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Guard deterministic provisioning from concurrent threads.
        with self.lock:
            # Guard deterministic provisioning from independent processes.
            with self._ledger_process_lock():
                # Complete every recoverable wallet action before changing players.
                self._recover_all_json_actions_locked()
                # Load the current player collection without seeding unrelated defaults.
                state = self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
                # Return an existing compatible row for an idempotent recovery attempt.
                for existing in state["players"]:
                    # Match only the deterministic invited-player identifier.
                    if existing.get("player_id") == player.get("player_id"):
                        # Reject an identifier collision with different ownership semantics.
                        if existing.get("type") != player.get("type"):
                            # Preserve the existing row and fail the provisioning saga closed.
                            raise ConflictError("Player provisioning identity conflicts with existing state")
                        # Return the already provisioned player without resetting balance or timestamps.
                        return existing
                # Detach and cents-normalize the new wallet before publication.
                inserted = {**player, "balance": _quantized_money(player.get("balance", 0))}
                # Append the validated copy so caller mutation cannot alter persisted state after return.
                state["players"].append(inserted)
                # Persist the complete deterministic player document while the process lock remains held.
                self._save_players_document(state)
                # Return the newly committed compatible row.
                return dict(inserted)

    # Return the empty committed-action registry shape used by fresh JSON stores.
    def _empty_action_registry(self) -> dict:
        # Return a versioned registry with a monotonic recovery order.
        return {"schema_version": 1, "next_sequence": 1, "actions": {}}

    # Build a deterministic registry key from the canonical storage identity.
    def _action_identity(self, player_id: str, scope: str, action_key: str) -> str:
        # Serialize identity fragments so delimiters inside caller keys remain unambiguous.
        return json.dumps([player_id, scope, action_key], separators=(",", ":"))

    # Decode one physical JSONL line using the historical malformed-line skipping semantics. (issue #412)
    def _decode_ledger_line(self, line: str) -> dict | None:
        # Start protected decoding so one malformed historical row does not block recovery.
        try:
            # Decode the candidate ledger row.
            event = json.loads(line)
        # Skip malformed rows consistently with the public recent-ledger reader.
        except Exception:
            # Report no row so callers continue to later append-only rows.
            return None
        # Keep dictionary rows that expose a ledger identity.
        if isinstance(event, dict) and event.get("ledger_id"):
            # Return the valid decoded event.
            return event
        # Report no row for identity-free payloads.
        return None

    # Read valid ledger rows in their append order for recovery checks.
    def _ledger_rows(self) -> list[dict]:
        # Stat the append-only file once so unchanged content skips every re-parse. (issue #412)
        try:
            # Read the current size and modification identity of the ledger file.
            stat = os.stat(self.ledger_path())
        # Treat a missing file as an empty ledger exactly like the previous implementation.
        except OSError:
            # Drop cache state left behind by a removed or reset ledger file. (issue #412)
            self._drop_ledger_cache()
            # Avoid opening an absent ledger file.
            return []
        # Serve cached rows when the file identity matches the last parse. (issue #412)
        if stat.st_size == self._ledger_cache_offset and stat.st_mtime_ns == self._ledger_cache_mtime_ns:
            # Return the cached append-order view without touching file contents.
            return self._ledger_cache_rows
        # Reload from the start after truncation or an equal-size rewrite. (issue #412)
        if stat.st_size <= self._ledger_cache_offset:
            # Drop the cache because append-only growth can no longer explain the observed file.
            self._drop_ledger_cache()
        # Read only the bytes appended after the cached offset. (issue #412)
        with self.ledger_path().open("rb") as handle:
            # Position the reader at the first unparsed byte.
            handle.seek(self._ledger_cache_offset)
            # Read exactly the appended region observed by the stat call.
            appended = handle.read(stat.st_size - self._ledger_cache_offset)
        # Split at the final newline so an unterminated trailing line is never cached. (issue #412)
        boundary = appended.rfind(b"\n") + 1
        # Decode complete lines with the same replacement policy as the previous full-file read.
        for line in appended[:boundary].decode("utf-8", errors="replace").splitlines():
            # Decode the candidate line with the historical malformed-line skipping.
            event = self._decode_ledger_line(line)
            # Keep dictionary rows that expose a ledger identity.
            if event is not None:
                # Add the valid event to the cached recovery view.
                self._ledger_cache_rows.append(event)
                # Index the same row reference by player for O(tail) filtered reads.
                self._ledger_cache_by_player.setdefault(event.get("player_id"), []).append(event)
                # Index the same row by immutable ledger identity for O(1) projection proof.
                self._ledger_cache_by_id[event["ledger_id"]] = event
        # Advance the cache offset past every fully terminated parsed line. (issue #412)
        self._ledger_cache_offset += boundary
        # Remember the file identity that produced the cached content. (issue #412)
        self._ledger_cache_mtime_ns = stat.st_mtime_ns
        # Re-decode unterminated trailing bytes each call without caching them. (issue #412)
        self._ledger_cache_tail_rows = [row for row in (self._decode_ledger_line(line) for line in appended[boundary:].decode("utf-8", errors="replace").splitlines()) if row is not None]
        # Return cached rows plus any uncacheable trailing rows in commit order.
        return self._ledger_cache_rows + self._ledger_cache_tail_rows if self._ledger_cache_tail_rows else self._ledger_cache_rows

    # Project one durably committed action into players.json and ledger.jsonl.
    def _project_committed_action(self, event: dict) -> None:
        # Refresh the incremental ledger cache before checking immutable identity membership. (issue #432)
        self._ledger_rows()
        # Stop when both balance and ledger projection already completed earlier.
        if event["ledger_id"] in self._ledger_cache_by_id:
            # Treat the ledger row as proof that this action was fully projected.
            return
        # Load the current player document without invoking another process lock.
        state = self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
        # Find the wallet owned by the committed action.
        player = next((row for row in state.get("players", []) if row.get("player_id") == event["player_id"]), None)
        # Fail closed when recovery cannot locate the committed wallet.
        if player is None:
            # Preserve the journal for operator recovery instead of discarding money state.
            raise ConflictError("Committed ledger action references a missing player", {"ledger_id": event["ledger_id"], "player_id": event["player_id"]})
        # Normalize the currently projected fake-money balance.
        current_balance = _quantized_money(player.get("balance", 0))
        # Apply the committed balance transition when projection stopped before players.json.
        if current_balance == _quantized_money(event["balance_before"]):
            # Move the wallet to the committed post-transaction balance exactly once.
            player["balance"] = _quantized_money(event["balance_after"])
            # Stamp recovery as a player update for downstream admin views.
            player["updated_at"] = utc_now()
            # Persist the recovered wallet state before appending the missing ledger row.
            self._save_players_document(state)
        # Accept a balance that already reached the committed after-state before a lost response.
        elif current_balance != _quantized_money(event["balance_after"]):
            # Reject divergent state because guessing could duplicate or erase later money actions.
            raise ConflictError("Committed ledger action cannot be recovered from divergent wallet state", {"ledger_id": event["ledger_id"], "balance": current_balance})
        # Append the original committed event after the wallet transition is durable.
        self._append_jsonl(self.ledger_path(), event)

    # Read a file identity without requiring the file to exist. (issue #432)
    def _optional_file_stat(self, path: Path) -> tuple[int, int] | None:
        # Start protected stat logic so absent compatibility files remain ordinary.
        try:
            # Read the file size and nanosecond modification identity.
            stat = os.stat(path)
        # Treat a missing path as an absent optional source.
        except OSError:
            # Return no identity for an absent optional file.
            return None
        # Return the stable pair used by the provider-local cache guard.
        return stat.st_size, stat.st_mtime_ns

    # Add the in-memory pending set required for bounded crash recovery. (LEDGER-034)
    def _normalize_actions_registry(self, registry: Any) -> dict:
        # Fail closed when a durable registry is not the expected object shape.
        if not isinstance(registry, dict) or not isinstance(registry.get("actions", {}), dict):
            # Reject inconsistent money-action state instead of silently rearming identities.
            raise ConflictError("Ledger action index is inconsistent")
        # Preserve the versioned registry shape used by existing stores.
        registry.setdefault("schema_version", 1)
        # Preserve a monotonic next sequence even for a legacy empty snapshot.
        registry.setdefault("next_sequence", 1)
        # Index only unprojected identities so steady-state recovery is O(pending), not O(history).
        registry["_pending"] = {identity for identity, record in registry["actions"].items() if isinstance(record, dict) and record.get("projected") is not True}
        # Return the normalized mutable in-memory view.
        return registry

    # Apply one durable append-only action-journal record to the cached registry. (LEDGER-034)
    def _apply_action_journal_record(self, registry: dict, record: Any) -> None:
        # Reject malformed records before they can weaken exactly-once identity state.
        if not isinstance(record, dict) or record.get("op") not in {"commit", "project", "settled"} or not isinstance(record.get("identity"), str):
            # Fail closed because skipping a corrupt commit could duplicate a money action.
            raise ConflictError("Ledger action journal is inconsistent")
        # Read the unambiguous canonical identity shared by both record kinds.
        identity = record["identity"]
        # Apply a logical commit before any compatible wallet projection.
        if record["op"] == "commit":
            # Read the immutable action record carried by the commit line.
            action = record.get("action")
            # Require every committed line to carry a structured event and monotonic sequence.
            if not isinstance(action, dict) or not isinstance(action.get("event"), dict) or not isinstance(action.get("sequence"), int):
                # Preserve the journal for operator recovery instead of guessing missing money state.
                raise ConflictError("Ledger action journal is inconsistent")
            # Read any previously committed identity from the legacy snapshot or earlier journal tail.
            existing = registry["actions"].get(identity)
            # Compare immutable fields while ignoring a later in-memory projection acknowledgement.
            comparable_existing = ({**existing, "projected": False} if isinstance(existing, dict) else existing)
            # Permit only byte-semantic duplicate commit records, which are harmless after a lost acknowledgement.
            if existing is not None and comparable_existing != action:
                # Reject two different immutable actions under one canonical identity.
                raise ConflictError("Ledger action journal identity conflicts", {"action_key": action.get("action_key")})
            # Publish the immutable action record into the provider-owned point index.
            registry["actions"][identity] = action
            # Mark the identity pending until a durable project record follows.
            registry["_pending"].add(identity)
            # Advance the next sequence beyond every accepted durable commit.
            registry["next_sequence"] = max(int(registry.get("next_sequence", 1)), int(action["sequence"]) + 1)
            # Stop after applying the commit record.
            return
        # Rebuild one compacted settled action from its immutable ledger row.
        if record["op"] == "settled":
            # Require compact records to retain monotonic order and ledger identity.
            if not isinstance(record.get("sequence"), int) or not isinstance(record.get("ledger_id"), str):
                # Fail closed on a compact record that cannot reconstruct exact action state.
                raise ConflictError("Ledger action journal is inconsistent")
            # Decode the canonical identity tuple carried unchanged through compaction.
            try:
                # Parse the unambiguous player, scope, and action-key fragments.
                identity_parts = json.loads(identity)
            # Normalize invalid identity JSON to the action-index recovery boundary.
            except json.JSONDecodeError:
                # Preserve compacted bytes for operator inspection.
                raise ConflictError("Ledger action journal is inconsistent") from None
            # Require exactly three string identity fragments.
            if not isinstance(identity_parts, list) or len(identity_parts) != 3 or any(not isinstance(part, str) for part in identity_parts):
                # Reject an identity that cannot match the provider write seam.
                raise ConflictError("Ledger action journal is inconsistent")
            # Refresh the append-only ledger cache before resolving the compact reference.
            self._ledger_rows()
            # Resolve the immutable event by its provider-owned ledger identity.
            event = self._ledger_cache_by_id.get(record["ledger_id"])
            # Require every settled compact record to reference one durable compatible row.
            if not isinstance(event, dict):
                # Fail closed instead of accepting an identity whose replay proof is missing.
                raise ConflictError("Ledger action journal requires operator recovery")
            # Read storage-owned fingerprint evidence from the committed event.
            details = event.get("details") if isinstance(event.get("details"), dict) else {}
            # Reconstruct the in-memory action record without retaining duplicate event bytes on disk.
            compact_action = {"sequence": record["sequence"], "player_id": identity_parts[0], "action_scope": identity_parts[1], "action_key": identity_parts[2], "action_fingerprint": details.get("ledger_action_fingerprint"), "projected": True, "event": event}
            # Read an optional matching legacy snapshot record.
            existing = registry["actions"].get(identity)
            # Reject a snapshot/journal disagreement on immutable ledger identity.
            if isinstance(existing, dict) and isinstance(existing.get("event"), dict) and existing["event"].get("ledger_id") != event.get("ledger_id"):
                # Preserve both sources for operator recovery.
                raise ConflictError("Ledger action journal identity conflicts", {"action_key": identity_parts[2]})
            # Publish the reconstructed point-index record.
            registry["actions"][identity] = compact_action
            # Keep the settled identity out of the bounded recovery set.
            registry["_pending"].discard(identity)
            # Advance the next sequence beyond the compact record.
            registry["next_sequence"] = max(int(registry.get("next_sequence", 1)), int(record["sequence"]) + 1)
            # Stop after applying the compact settled record.
            return
        # Read the corresponding committed action before accepting its projection marker.
        action = registry["actions"].get(identity)
        # Require a project record to refer to one known immutable commit.
        if not isinstance(action, dict) or not isinstance(action.get("event"), dict):
            # Fail closed on orphan projection markers.
            raise ConflictError("Ledger action journal is inconsistent")
        # Require the marker to bind the exact committed ledger event identity.
        if record.get("ledger_id") != action["event"].get("ledger_id"):
            # Reject a marker that could acknowledge a different wallet transition.
            raise ConflictError("Ledger action journal projection conflicts", {"action_key": action.get("action_key")})
        # Mark the compatible-file projection complete after its durable marker is read.
        action["projected"] = True
        # Remove the settled identity from the bounded recovery set.
        registry["_pending"].discard(identity)

    # Parse complete append-only journal bytes and apply them in durable order. (LEDGER-034)
    def _apply_action_journal_bytes(self, registry: dict, payload: bytes) -> None:
        # Require a newline-terminated tail because a partial commit cannot be ignored safely.
        if payload and not payload.endswith(b"\n"):
            # Fail closed until an operator resolves the interrupted append.
            raise ConflictError("Ledger action journal requires operator recovery")
        # Visit each physical record in append order.
        for line in payload.splitlines():
            # Reject blank records because the format is one object per line.
            if not line:
                # Preserve the journal rather than accepting an ambiguous gap.
                raise ConflictError("Ledger action journal is inconsistent")
            # Start protected JSON decoding for one durable line.
            try:
                # Decode the UTF-8 JSON object without replacement semantics.
                record = json.loads(line.decode("utf-8"))
            # Normalize malformed bytes to the public fail-closed conflict boundary.
            except (UnicodeDecodeError, json.JSONDecodeError):
                # Preserve the journal for explicit operator recovery.
                raise ConflictError("Ledger action journal is inconsistent") from None
            # Apply the validated record to the in-memory index.
            self._apply_action_journal_record(registry, record)

    # Read the committed-action registry from one legacy snapshot plus an incremental journal. (LEDGER-034)
    def _read_actions_registry(self) -> Any:
        # Discover interrupted compaction files before trusting either durable source.
        temporaries = tuple(self.data_dir.glob("ledger_actions.jsonl.tmp-*"))
        # Fail closed while any unpublished checkpoint remains unresolved.
        if temporaries:
            # Preserve the old journal and temporary bytes for operator comparison.
            raise ConflictError("Ledger action journal requires operator recovery")
        # Capture the optional legacy snapshot identity before deciding whether the cache is reusable.
        snapshot_stat = self._optional_file_stat(self.ledger_actions_path())
        # Capture the optional append-only journal identity under the held process lock.
        journal_stat = self._optional_file_stat(self.ledger_action_journal_path())
        # Require an absent journal to stay absent, or an existing journal to grow monotonically.
        journal_monotonic = (journal_stat is None and self._actions_cache_journal_stat is None) or (journal_stat is not None and journal_stat[0] >= self._actions_cache_journal_offset)
        # Reuse the cached registry when the immutable snapshot is unchanged and the journal only grew.
        cache_reusable = self._actions_cache_registry is not None and self._actions_cache_snapshot_stat == snapshot_stat and journal_monotonic
        # Refresh only the new journal tail for the ordinary multi-process append case.
        if cache_reusable:
            # Return immediately when the journal identity is byte-for-byte unchanged.
            if self._actions_cache_journal_stat == journal_stat:
                # Reuse the existing provider-owned point index.
                return self._actions_cache_registry
            # Reject a same-size rewrite because append-only history must never change in place.
            if journal_stat is not None and journal_stat[0] == self._actions_cache_journal_offset:
                # Force a complete validation rebuild below.
                cache_reusable = False
            # Apply only bytes appended by another process when the file grew monotonically.
            elif journal_stat is not None:
                # Open the journal in binary mode so offsets are platform-independent.
                with self.ledger_action_journal_path().open("rb") as handle:
                    # Seek to the first unapplied durable byte.
                    handle.seek(self._actions_cache_journal_offset)
                    # Read exactly the newly observed append-only tail.
                    payload = handle.read(journal_stat[0] - self._actions_cache_journal_offset)
                # Apply the complete tail to the existing point index.
                self._apply_action_journal_bytes(self._actions_cache_registry, payload)
                # Advance the parsed offset to the observed durable file size.
                self._actions_cache_journal_offset = journal_stat[0]
                # Bind the refreshed cache to the new journal identity.
                self._actions_cache_journal_stat = journal_stat
                # Return the incrementally refreshed registry.
                return self._actions_cache_registry
            # Return the cached snapshot-derived registry when no journal exists.
            elif journal_stat is None:
                # Keep the zero journal offset bound to an absent journal.
                self._actions_cache_journal_offset = 0
                # Remember that no journal identity exists.
                self._actions_cache_journal_stat = None
                # Return the cached registry without reparsing the snapshot.
                return self._actions_cache_registry
        # Build one call-local sentinel that only legacy snapshot corruption can return.
        sentinel = object()
        # Read the existing compatible snapshot when one exists.
        parsed = self._read_json(self.ledger_actions_path(), lambda: sentinel) if snapshot_stat is not None else self._empty_action_registry()
        # Refuse to forget durable identities when the legacy snapshot cannot be decoded.
        if parsed is sentinel:
            # Drop process-local cache state before surfacing the recovery boundary.
            self._drop_actions_cache()
            # Fail closed instead of returning an empty action registry.
            raise ConflictError("Ledger action index requires operator recovery")
        # Normalize the snapshot and build its bounded pending set.
        registry = self._normalize_actions_registry(parsed)
        # Apply the complete journal after the legacy snapshot baseline.
        if journal_stat is not None:
            # Read the exact bytes observed by the pre-read stat call.
            with self.ledger_action_journal_path().open("rb") as handle:
                # Read only the stable length captured while the process lock is held.
                payload = handle.read(journal_stat[0])
            # Apply every complete append-only record in order.
            self._apply_action_journal_bytes(registry, payload)
        # Cache the combined provider-owned action index.
        self._actions_cache_registry = registry
        # Bind the cache to the legacy snapshot identity.
        self._actions_cache_snapshot_stat = snapshot_stat
        # Record the complete applied journal length.
        self._actions_cache_journal_offset = journal_stat[0] if journal_stat is not None else 0
        # Bind the cache to the append-only journal identity.
        self._actions_cache_journal_stat = journal_stat
        # Treat a completely validated restart image as the next bounded-growth baseline.
        self._actions_cache_compaction_floor = journal_stat[0] if journal_stat is not None else 0
        # Return the combined compatible registry.
        return registry

    # Durably append one action record and update the already-locked cache. (LEDGER-034)
    def _append_action_journal_record(self, registry: dict, record: dict) -> None:
        # Reject planner-side mutation before opening the durable journal.
        self._reject_planner_mutation()
        # Ensure the ordinary provider directories exist before appending.
        self.ensure_ready()
        # Serialize the record deterministically with one platform-independent newline.
        payload = (json.dumps(record, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
        # Create the target parent without touching any unrelated data path.
        self.ledger_action_journal_path().parent.mkdir(parents=True, exist_ok=True)
        # Open the append-only journal in binary mode so byte offsets and newlines are stable.
        with self.ledger_action_journal_path().open("ab") as handle:
            # Append the complete logical commit or projection marker in one write call.
            handle.write(payload)
            # Flush Python buffering before requesting filesystem durability.
            handle.flush()
            # Require the journal bytes to reach the operating-system durable boundary.
            os.fsync(handle.fileno())
        # Apply the just-persisted record to the caller's in-memory registry.
        self._apply_action_journal_record(registry, record)
        # Refresh the journal identity after the durable append.
        journal_stat = self._optional_file_stat(self.ledger_action_journal_path())
        # Fail closed if the just-written journal cannot be stated.
        if journal_stat is None:
            # Preserve all files for operator recovery.
            raise ConflictError("Ledger action journal requires operator recovery")
        # Cache the caller registry containing this exact durable record.
        self._actions_cache_registry = registry
        # Bind the cache to the unchanged legacy snapshot identity.
        self._actions_cache_snapshot_stat = self._optional_file_stat(self.ledger_actions_path())
        # Advance the parsed offset to the complete durable journal size.
        self._actions_cache_journal_offset = journal_stat[0]
        # Bind the cache to the current journal identity.
        self._actions_cache_journal_stat = journal_stat

    # Rewrite a bounded journal checkpoint without duplicate settled event payloads. (LEDGER-034)
    def _compact_action_journal(self, registry: dict) -> None:
        # Order records by their monotonic logical commit sequence.
        ordered = sorted(registry.get("actions", {}).items(), key=lambda item: int(item[1].get("sequence", 0)))
        # Build one compact or pending record for every durable action identity.
        records = []
        # Visit each committed identity exactly once.
        for identity, action in ordered:
            # Store only a ledger reference after compatible projection is durable.
            if action.get("projected") is True:
                # Append one compact settled record without duplicate event bytes.
                records.append({"op": "settled", "identity": identity, "sequence": int(action["sequence"]), "ledger_id": action["event"]["ledger_id"]})
            # Preserve the complete immutable event while crash recovery remains pending.
            else:
                # Append one full logical commit record for the unresolved crash window.
                records.append({"op": "commit", "identity": identity, "action": action})
        # Serialize every checkpoint record with stable binary newlines.
        payload = b"".join((json.dumps(record, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8") for record in records)
        # Build a process-and-thread-unique sibling used for atomic publication.
        tmp = self.ledger_action_journal_path().with_suffix(f".jsonl.tmp-{os.getpid()}-{threading.get_ident()}")
        # Write the complete checkpoint without exposing partial replacement bytes.
        with tmp.open("wb") as handle:
            # Publish the exact compact payload into the private temporary file.
            handle.write(payload)
            # Flush Python buffering before the durability boundary.
            handle.flush()
            # Require the complete compact checkpoint to reach durable storage.
            os.fsync(handle.fileno())
        # Retry bounded Windows sharing violations while preserving atomic replacement.
        for attempt in range(20):
            # Start protected replacement so transient scanner handles can release.
            try:
                # Atomically replace the old append-only history with its equivalent checkpoint.
                tmp.replace(self.ledger_action_journal_path())
                # Stop after successful checkpoint publication.
                break
            # Handle only transient Windows sharing failures.
            except PermissionError:
                # Surface the final failure without deleting recovery bytes.
                if attempt == 19:
                    # Re-raise the original filesystem failure.
                    raise
                # Wait one bounded increasing interval before retrying.
                time.sleep(0.01 * (attempt + 1))
        # Read the newly published journal identity.
        journal_stat = self._optional_file_stat(self.ledger_action_journal_path())
        # Require the checkpoint file to remain visible after atomic publication.
        if journal_stat is None:
            # Fail closed while preserving the provider directory for recovery.
            raise ConflictError("Ledger action journal requires operator recovery")
        # Keep the already-equivalent in-memory point index cached.
        self._actions_cache_registry = registry
        # Bind the cache to the unchanged legacy compatibility snapshot.
        self._actions_cache_snapshot_stat = self._optional_file_stat(self.ledger_actions_path())
        # Mark the entire compact checkpoint as parsed.
        self._actions_cache_journal_offset = journal_stat[0]
        # Bind the cache to the compact journal identity.
        self._actions_cache_journal_stat = journal_stat
        # Measure the next compaction only after another full threshold of append-only growth.
        self._actions_cache_compaction_floor = journal_stat[0]

    # Compact only after a bounded amount of append-only growth. (LEDGER-034)
    def _maybe_compact_action_journal(self, registry: dict) -> None:
        # Read the current journal identity after a completed projection marker.
        journal_stat = self._optional_file_stat(self.ledger_action_journal_path())
        # Keep ordinary actions append-only until the configured growth threshold is reached.
        if journal_stat is None or journal_stat[0] - self._actions_cache_compaction_floor < _LEDGER_ACTION_COMPACT_BYTES:
            # Return without any whole-history write in the common path.
            return
        # Publish one compact equivalent checkpoint at the bounded threshold.
        self._compact_action_journal(registry)

    # Recover only unprojected journaled actions before allowing a later wallet mutation. (LEDGER-034)
    def _recover_committed_actions(self, registry: dict | None = None) -> dict:
        # Load the combined snapshot/journal index when the caller did not pass one.
        registry = registry or self._read_actions_registry()
        # Read the canonical action map from the normalized registry.
        actions = registry.get("actions", {})
        # Resolve only pending identities in original monotonic order.
        pending = sorted((actions[identity] for identity in tuple(registry.get("_pending", set()))), key=lambda item: int(item.get("sequence", 0)))
        # Replay each crash-window transition exactly once.
        for action in pending:
            # Project the immutable event into compatible wallet and ledger files.
            self._project_committed_action(action["event"])
            # Rebuild the canonical identity used by the journal marker.
            identity = self._action_identity(action["player_id"], action["action_scope"], action["action_key"])
            # Durably acknowledge the completed projection without rewriting historical actions.
            self._append_action_journal_record(registry, {"op": "project", "identity": identity, "ledger_id": action["event"]["ledger_id"]})
        # Compact only after all recoverable actions have durable projection markers.
        self._maybe_compact_action_journal(registry)
        # Return the settled registry so the transaction can reuse its in-memory view.
        return registry

    # Execute a ledger transaction after both thread and process locks are held.
    def _transact_ledger_locked(self, player_id: str, amount: float, transaction_type: str, game: str | None, round_id: str | None, details: dict | None) -> dict:
        # Load the player document using an empty fallback for clear not-found errors.
        state = self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
        # Find the requested player in the document.
        player = next((row for row in state["players"] if row["player_id"] == player_id), None)
        # Raise a consistent not-found error when no player exists.
        if player is None:
            # Raise the same player lookup error shape used by players.get_player.
            raise NotFoundError(f"Player {player_id} was not found")
        # Capture the balance before the proposed mutation.
        before = _quantized_money(player.get("balance", 0))
        # Compute the balance after the proposed mutation.
        after = _quantized_money(Decimal(str(before)) + Decimal(str(amount)))
        # Reject transactions that would overdraw the fake-money wallet.
        if after < 0:
            # Raise the existing insufficient-funds error with ledger details.
            raise InsufficientFundsError(details={"player_id": player_id, "balance": before, "amount": amount, "transaction_type": transaction_type})
        # Store the new balance on the player row.
        player["balance"] = after
        # Stamp the player update time alongside the balance mutation.
        player["updated_at"] = utc_now()
        # Build the ledger event before persistence so both stores agree.
        event = _ledger_event(player_id, amount, transaction_type, before, after, game, round_id, details)
        # Persist the player document before appending the ledger row under the same lock.
        self._save_players_document(state)
        # Append the ledger event while the compound transaction lock is still held.
        self._append_jsonl(self.ledger_path(), event)
        # Return the committed ledger event to the caller.
        return event

    # Execute a ledger transaction and balance update under thread and process locks.
    def transact_ledger(self, player_id: str, amount: float, transaction_type: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> dict:
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Normalize the transaction amount to the app's fake-money precision.
        amount = _quantized_money(amount)
        # Reject zero-value ledger rows before touching player state.
        if amount == 0:
            # Raise a validation error consistent with the previous ledger module.
            raise ValidationError("Ledger transaction amount cannot be zero")
        # Guard the wallet transaction from concurrent threads in this process.
        with self.lock:
            # Guard the wallet transaction from independent application processes.
            with self._ledger_process_lock():
                # Complete every recoverable wallet action before applying a later mutation.
                self._recover_all_json_actions_locked()
                # Execute the existing compatible transaction inside both locks.
                return self._transact_ledger_locked(player_id, amount, transaction_type, game, round_id, details)

    # Execute or replay one storage-enforced JSON ledger action identity.
    def transact_ledger_once(self, player_id: str, amount: float, transaction_type: str, action_key: str, game: str | None = None, round_id: str | None = None, details: dict | None = None) -> tuple[dict, bool]:
        # Reject wallet mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Normalize the transaction amount to the app's fake-money precision.
        amount = _quantized_money(amount)
        # Reject zero-value ledger rows before touching durable action state.
        if amount == 0:
            # Raise the standard ledger validation error.
            raise ValidationError("Ledger transaction amount cannot be zero")
        # Normalize the caller-owned identity fragment before storage lookup.
        action_key = _normalize_action_key(action_key)
        # Derive the game-or-core namespace used by both storage providers.
        scope = _action_scope(game)
        # Derive the semantic digest that distinguishes replay from changed reuse.
        fingerprint = _action_fingerprint(amount, transaction_type, game, round_id, details)
        # Build the unambiguous JSON registry key.
        identity = self._action_identity(player_id, scope, action_key)
        # Guard the action from concurrent threads in this process.
        with self.lock:
            # Guard the action from independent application processes.
            with self._ledger_process_lock():
                # Complete every legacy and provider-private wallet action in fixed order.
                self._recover_all_json_actions_locked()
                # Reload the settled legacy registry for this transaction's identity lookup.
                registry = self._recover_committed_actions()
                # Read an earlier commit for this identity when a retry arrives.
                existing = registry.get("actions", {}).get(identity)
                # Return the original event for an exact semantic replay.
                if existing is not None:
                    # Reject changed reuse before returning any prior money result.
                    _validate_action_replay(existing["event"], fingerprint, action_key)
                    # Return the original event with an explicit replay marker.
                    return existing["event"], True
                # Enrich details with storage-owned audit metadata only after hashing caller semantics.
                committed_details = _action_details(details, action_key, fingerprint)
                # Build the candidate wallet transition without persisting it yet.
                state = self._load_players_document(lambda: {"schema_version": SCHEMA_VERSION, "players": []})
                # Find the wallet that owns this action identity.
                player = next((row for row in state["players"] if row["player_id"] == player_id), None)
                # Reject unknown players before writing the action journal.
                if player is None:
                    # Raise the standard player lookup error.
                    raise NotFoundError(f"Player {player_id} was not found")
                # Capture the balance before the proposed mutation.
                before = _quantized_money(player.get("balance", 0))
                # Compute the balance after the proposed mutation.
                after = _quantized_money(Decimal(str(before)) + Decimal(str(amount)))
                # Reject actions that would overdraw the fake-money wallet.
                if after < 0:
                    # Raise the standard insufficient-funds error before committing the identity.
                    raise InsufficientFundsError(details={"player_id": player_id, "balance": before, "amount": amount, "transaction_type": transaction_type})
                # Build the immutable event returned by every later replay.
                event = _ledger_event(player_id, amount, transaction_type, before, after, game, round_id, committed_details)
                # Allocate the next monotonic recovery sequence.
                sequence = int(registry.get("next_sequence", 1))
                # Build the immutable action record stored before compatible projection.
                action = {"sequence": sequence, "player_id": player_id, "action_scope": scope, "action_key": action_key, "action_fingerprint": fingerprint, "projected": False, "event": event}
                # Append the logical commit durably without rewriting prior action history. (LEDGER-034)
                self._append_action_journal_record(registry, {"op": "commit", "identity": identity, "action": action})
                # Project the committed transition into the compatible player and ledger files.
                self._project_committed_action(event)
                # Append one compact marker after both compatible projections succeed. (LEDGER-034)
                self._append_action_journal_record(registry, {"op": "project", "identity": identity, "ledger_id": event["ledger_id"]})
                # Compact only after bounded journal growth and a complete settled action.
                self._maybe_compact_action_journal(registry)
                # Return the newly committed event with a non-replay marker.
                return event, False

    # Find one committed JSON ledger action without scanning ledger history. (LEDGER-033)
    def find_ledger_action(self, player_id: str, game: str | None, action_key: str) -> dict | None:
        # Normalize the indexed caller-owned key before durable lookup.
        action_key = _normalize_action_key(action_key)
        # Normalize the game-or-core namespace exactly as the write path does.
        scope = _action_scope(game)
        # Build the identical unambiguous key used by transact_ledger_once.
        identity = self._action_identity(player_id, scope, action_key)
        # Serialize recovery and lookup with local provider operations.
        with self.lock:
            # Serialize recovery and lookup with independent JSON provider processes.
            with self._ledger_process_lock():
                # Complete every durable logical commit before exposing its event.
                self._recover_all_json_actions_locked()
                # Read the stat-guarded action index once after recovery settles it.
                registry = self._read_actions_registry()
                # Read the indexed record without traversing unrelated actions.
                record = registry.get("actions", {}).get(identity) if isinstance(registry, dict) else None
                # Report a miss without falling back to unbounded ledger history.
                if not isinstance(record, dict):
                    # Preserve the public optional-result contract.
                    return None
                # Read the immutable committed event stored by the logical action journal.
                event = record.get("event")
                # Fail closed when an indexed record lacks a structured event.
                if not isinstance(event, dict):
                    # Reject corrupt action-index state instead of authorizing a fresh write.
                    raise ConflictError("Ledger action index is inconsistent", {"action_key": action_key})
                # Return a detached event so readers cannot mutate the provider cache.
                return copy.deepcopy(event)

    # Read recent ledger events from the local JSONL file.
    def read_ledger_recent(self, player_id: str | None = None, limit: int = 100) -> list[dict]:
        # Guard recovery and the ledger read from concurrent local threads.
        with self.lock:
            # Guard recovery and the ledger read from independent processes.
            with self._ledger_process_lock():
                # Complete every recoverable wallet action before exposing ledger state.
                self._recover_all_json_actions_locked()
                # Read all valid append-only rows after refreshing the incremental cache. (issue #412)
                rows = self._ledger_rows()
                # Apply the optional player filter used by player and Admin history views.
                if player_id is not None:
                    # Filter the combined view directly while rare unterminated trailing rows exist. (issue #412)
                    if self._ledger_cache_tail_rows:
                        # Keep only events owned by the requested player.
                        rows = [event for event in rows if event.get("player_id") == player_id]
                    # Use the per-player index for the ordinary fully-cached case. (issue #412)
                    else:
                        # Keep only events owned by the requested player without scanning other wallets.
                        rows = self._ledger_cache_by_player.get(player_id, [])
                # Return the requested tail of matching rows.
                return rows[-limit:]

    # Append a CSV history row using the existing local file format.
    def append_history(self, event: dict) -> None:
        # Reject provider mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Import csv only for the JSON provider's CSV compatibility path.
        import csv
        # Serialize history mutation with reset and every provider operation.
        with self.lock:
            # Hold the stable and legacy process gates across the complete append.
            with self._json_global_gate():
                # Complete every recoverable action before exposing a later history row.
                self._recover_all_json_actions_locked()
                # Store whether the history file already exists before opening it.
                exists = self.history_path().exists()
                # Open the CSV file in append mode using the existing newline settings.
                with self.history_path().open("a", newline="", encoding="utf-8") as handle:
                    # Build a DictWriter with the canonical history columns.
                    writer = csv.DictWriter(handle, fieldnames=HISTORY_FIELDS)
                    # Write a header for a fresh history file.
                    if not exists:
                        # Persist the CSV header before the first data row.
                        writer.writeheader()
                    # Append the normalized history event.
                    writer.writerow(event)

    # Read recent history rows from the local CSV file.
    def recent_history(self, limit: int = 100, game: str | None = None) -> list[dict]:
        # Import csv only for the JSON provider's CSV compatibility path.
        import csv
        # Serialize history visibility with reset and every provider operation.
        with self.lock:
            # Hold the stable and legacy process gates across the complete read.
            with self._json_global_gate():
                # Complete every recoverable action before exposing history.
                self._recover_all_json_actions_locked()
                # Return no history for fresh local runs.
                if not self.history_path().exists():
                    # Return an empty result set when there is no local CSV yet.
                    return []
                # Open the CSV file using the existing newline settings.
                with self.history_path().open("r", newline="", encoding="utf-8") as handle:
                    # Decode every history row into dictionaries.
                    rows = list(csv.DictReader(handle))
                # Apply optional game filtering for admin and casino history endpoints.
                if game:
                    # Keep only rows for the requested game.
                    rows = [row for row in rows if row.get("game") == game]
                # Return the requested tail of matching rows.
                return rows[-limit:]

    # Read a named JSON document from local storage.
    def read_document(self, key: str, default: Any) -> Any:
        # Guard recovery and document reads from concurrent local threads.
        with self.lock:
            # Bridge the provider-wide and shipped per-document process locks.
            with self._document_process_lock(key):
                # Complete every recoverable action before exposing documents.
                self._recover_all_json_actions_locked()
                # Reuse the local JSON helper for settings documents.
                return self._read_json(self.document_path(key), default)

    # Read one local security document strictly without fallback backups or normalization.
    def read_document_strict(self, key: str, default: Any, validator: Callable[[Any], bool] | None = None) -> Any:
        # Guard recovery and strict document reads from concurrent local threads.
        with self.lock:
            # Bridge the provider-wide and shipped per-document process locks.
            with self._document_process_lock(key):
                # Complete every recoverable action before exposing documents.
                self._recover_all_json_actions_locked()
                # Resolve the exact durable document path once under both locks.
                path = self.document_path(key)
                # Read actual bytes so only FileNotFoundError can select the reviewed default.
                try:
                    # Read the exact stored payload without a separate existence check.
                    encoded = path.read_bytes()
                # Treat only a truly absent path as the missing-document compatibility case.
                except FileNotFoundError:
                    # Preserve lazy default-factory behavior without creating the document.
                    value = default() if callable(default) else default
                # Collapse every other filesystem failure without leaking its path or detail.
                except OSError:
                    # Refuse with one fixed value-free operator-recovery boundary.
                    raise RuntimeError("Stored document requires operator recovery") from None
                # Decode bytes that were read successfully without invoking backup behavior.
                else:
                    # Start protected decoding while preserving the original bytes on failure.
                    try:
                        # Decode UTF-8 JSON with exact duplicate-key rejection.
                        value = json.loads(encoded.decode("utf-8"), object_pairs_hook=self._unique_json_object)
                    # Collapse malformed text, duplicate-key, deep, and numeric-limit failures.
                    except (UnicodeError, ValueError, RecursionError):
                        # Refuse with one fixed value-free operator-recovery boundary.
                        raise RuntimeError("Stored document requires operator recovery") from None
                # Require any caller-owned security shape without reflecting its contents.
                return _validated_strict_document(value, validator)

    # Write a named JSON document to local storage.
    def write_document(self, key: str, data: Any) -> None:
        # Reject provider mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Guard recovery and document writes from concurrent local threads.
        with self.lock:
            # Bridge the provider-wide and shipped per-document process locks.
            with self._document_process_lock(key):
                # Complete every recoverable action before overwriting a document.
                self._recover_all_json_actions_locked()
                # Reuse the local JSON helper for settings documents.
                self._write_json(self.document_path(key), data)

    # Mutate one local document under the provider lock for direct provider callers.
    def update_document(self, key: str, mutator: Callable[[Any], Any], default: Any, validator: Callable[[Any], bool] | None = None) -> Any:
        # Reject provider mutation attempted from inside a planner.
        self._reject_planner_mutation()
        # Serialize the direct provider read-modify-write inside this process.
        with self.lock:
            # Hold the same sidecar lock across every provider instance and process.
            with self._document_process_lock(key):
                # Complete every recoverable action before document mutation.
                self._recover_all_json_actions_locked()
                # Resolve the exact document path once under the cross-process lock.
                path = self.document_path(key)
                # Use the no-side-effect decoder only for a validator-bound security transaction.
                if validator is not None:
                    # Read actual text so only FileNotFoundError can select the default.
                    try:
                        # Read the exact current text while both process locks remain held.
                        encoded = path.read_bytes()
                    # Treat only a truly absent document as the reviewed initial state.
                    except FileNotFoundError:
                        # Preserve lazy default-factory behavior for a new document.
                        current = default() if callable(default) else default
                    # Collapse every other filesystem failure without path disclosure.
                    except OSError:
                        # Abort without a backup, temp, normalization, or mutator invocation.
                        raise RuntimeError("Stored document requires operator recovery") from None
                    # Decode an existing security document strictly under the update lock.
                    else:
                        # Start protected parsing while preserving the exact source bytes.
                        try:
                            # Reject invalid UTF-8, invalid JSON, and duplicate object keys.
                            current = json.loads(encoded.decode("utf-8"), object_pairs_hook=self._unique_json_object)
                        # Collapse every bounded parser failure into the fixed recovery boundary.
                        except (UnicodeError, ValueError, RecursionError):
                            # Abort without a backup, temp, normalization, or mutator invocation.
                            raise RuntimeError("Stored document requires operator recovery") from None
                # Preserve the legacy ordinary update decoder and corruption-backup semantics.
                elif not path.exists():
                    # Preserve lazy default-factory behavior for ordinary new documents.
                    current = default() if callable(default) else default
                # Parse an existing ordinary document through its unchanged last-key-wins decoder.
                else:
                    # Start protected legacy parsing.
                    try:
                        # Decode with the established ordinary document behavior.
                        current = json.loads(path.read_text(encoding="utf-8"))
                    # Preserve malformed state through the established backup path.
                    except json.JSONDecodeError:
                        # Copy the malformed payload for explicit recovery without replacing the source.
                        backup = path.with_suffix(path.suffix + f".corrupt-{int(time.time())}")
                        # Preserve a recoverable snapshot before aborting the mutation.
                        shutil.copy2(path, backup)
                        # Abort without invoking the mutator or writing a normalized document.
                        raise RuntimeError("Stored document requires operator recovery") from None
                # Validate the current security document while the complete transaction remains held.
                current = _validated_strict_document(current, validator)
                # Apply the caller-owned mutation while both process and thread locks are held.
                updated = mutator(current)
                # Atomically replace the complete JSON document only after successful validation and mutation.
                self._write_json(path, updated)
                # Return the exact value that was persisted.
                return updated
