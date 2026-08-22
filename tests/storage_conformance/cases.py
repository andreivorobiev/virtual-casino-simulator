# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Unchanged provider-neutral conformance groups A-J. (STORAGE-025, TEST-257)"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import threading
from typing import Callable

from casino.core.storage.base import HISTORY_FIELDS, StorageProvider
from casino.errors import CasinoError, ConflictError, InsufficientFundsError, NotFoundError, ValidationError


@dataclass(frozen=True)
class CaseContext:
    """Supply only the public provider contract and concurrency declaration to cases."""

    provider: StorageProvider
    supports_true_concurrency: bool


@dataclass(frozen=True)
class ConformanceGroup:
    """Bind one stable group identifier to its unchanged provider-neutral case."""

    identifier: str
    label: str
    run: Callable[[CaseContext], None]


class _InjectedFailure(RuntimeError):
    """Represent a caller failure used to prove transactional non-publication."""


def _require(condition: bool, message: str) -> None:
    """Raise a stable assertion even when Python optimization is enabled."""

    if not condition:
        raise AssertionError(message)


def _expect(error_type: type[BaseException], operation: Callable[[], object]) -> BaseException:
    """Return the expected failure or reject success and foreign exceptions."""

    try:
        operation()
    except error_type as error:
        return error
    except BaseException as error:
        raise AssertionError(f"expected {error_type.__name__}, received {type(error).__name__}") from error
    raise AssertionError(f"expected {error_type.__name__}, operation succeeded")


def _player(player_id: str, balance: float = 0.0, *, kind: str = "human") -> dict:
    """Build one complete provider-compatible synthetic wallet row."""

    return {
        "player_id": player_id,
        "display_name": f"Conformance {player_id}",
        "type": kind,
        "balance": balance,
        "created_at": "2026-08-22T00:00:00.000Z",
        "updated_at": "2026-08-22T00:00:00.000Z",
        "status": "active",
    }


def _players(*rows: dict) -> dict:
    """Wrap detached player rows in the durable document contract."""

    return {"schema_version": 1, "players": [dict(row) for row in rows]}


def _empty_players() -> dict:
    """Return a fresh empty wallet document for provider reads."""

    return _players()


def _history_event(index: int, game: str) -> dict:
    """Build one complete history row with deterministic provider-neutral values."""

    return {
        "timestamp": f"2026-08-22T00:00:0{index}.000Z",
        "game": game,
        "round_id": f"round-{index}",
        "player_id": "history-player",
        "bet_type": "straight",
        "bet_label": f"Bet {index}",
        "amount": float(index),
        "outcome": "win" if index % 2 else "lose",
        "payout": float(index * 2),
        "balance_after": float(100 + index),
        "details_json": json.dumps({"index": index}, sort_keys=True),
        "schema_version": 1,
    }


def _assert_gapless_wallet_chain(events: list[dict], initial_balance: Decimal) -> None:
    """Treat public append order plus adjacent wallet boundaries as the gapless sequence."""

    expected_before = initial_balance
    seen_ids: set[str] = set()
    for event in events:
        ledger_id = str(event.get("ledger_id", ""))
        _require(bool(ledger_id) and ledger_id not in seen_ids, "ledger order contained a missing or duplicate identity")
        seen_ids.add(ledger_id)
        observed_before = Decimal(str(event["balance_before"]))
        observed_amount = Decimal(str(event["amount"]))
        observed_after = Decimal(str(event["balance_after"]))
        _require(observed_before == expected_before, "per-player ledger sequence contains a balance gap")
        _require(observed_after == observed_before + observed_amount, "ledger event balance arithmetic is inconsistent")
        expected_before = observed_after


def _document_basics(provider: StorageProvider, prefix: str) -> None:
    """Exercise the small group-A contract reused after a reset."""

    key = f"{prefix}/nested/settings"
    default_calls: list[str] = []

    def default_factory() -> dict:
        default_calls.append("called")
        return {"missing": True}

    missing = provider.read_document(key, default_factory)
    _require(missing == {"missing": True} and default_calls == ["called"], "missing document default contract changed")
    _require(not provider.document_exists(key), "reading a missing document created durable state")
    payload = {"nested": {"locale": "ru-RU", "label": "казино 🎰"}, "items": [1, 2, 3]}
    provider.write_document(key, payload)
    _require(provider.document_exists(key), "written document is not visible")
    _require(provider.read_document(key, {}) == payload, "nested unicode document did not round-trip")
    updated = provider.update_document(key, lambda current: {**current, "counter": current.get("counter", 0) + 1}, {})
    _require(updated["counter"] == 1 and provider.read_document(key, {}) == updated, "atomic document update was not published")


def group_a_documents(context: CaseContext) -> None:
    """A. Verify document round-trip, strictness, translation, size, and atomicity."""

    provider = context.provider
    _document_basics(provider, "conformance/a")
    large_key = "conformance/a/large"
    large_payload = {"blob": "x" * (1024 * 1024), "unicode": "данные"}
    provider.write_document(large_key, large_payload)
    _require(provider.read_document(large_key, {}) == large_payload, ">=1 MiB document did not round-trip")
    strict_missing = provider.read_document_strict("conformance/a/strict-missing", lambda: {"valid": True}, lambda value: value == {"valid": True})
    _require(strict_missing == {"valid": True}, "strict missing document did not use its reviewed default")
    _require(not provider.document_exists("conformance/a/strict-missing"), "strict missing read created durable state")
    provider.write_document("conformance/a/strict-invalid", {"valid": False, "secret": "must-not-escape"})
    strict_error = _expect(RuntimeError, lambda: provider.read_document_strict("conformance/a/strict-invalid", {}, lambda value: value.get("valid") is True))
    _require(str(strict_error) == "Stored document requires operator recovery", "strict corruption exposed provider or payload detail")
    stable_key = "conformance/a/atomic-failure"
    provider.write_document(stable_key, {"value": 1})

    def fail_after_mutation(current: dict) -> dict:
        current["value"] = 2
        raise _InjectedFailure("caller stopped")

    _expect(_InjectedFailure, lambda: provider.update_document(stable_key, fail_after_mutation, {}))
    _require(provider.read_document(stable_key, {}) == {"value": 1}, "failed document update leaked partial state")
    with tempfile.TemporaryDirectory(prefix="storage-conformance-path-") as directory:
        data_root = Path(directory).resolve()
        target = data_root / "nested" / "state.json"
        reference = provider.document_reference(target, data_root)
        _require(str(reference).replace("\\", "/").endswith("nested/state.json"), "document path translation lost its stable suffix")


def group_b_players(context: CaseContext) -> None:
    """B. Verify player lifecycle, duplicate rules, lookup, and normalization reports."""

    provider = context.provider
    first = _player("player-a", 12.34)
    inserted = provider.insert_player(first)
    _require(inserted["player_id"] == "player-a" and inserted["balance"] == 12.34, "player insert changed the wallet")
    _require(provider.get_player("player-a", _empty_players) == inserted, "point player read did not return the inserted row")
    duplicate = provider.insert_player({**first, "balance": 999.0})
    _require(duplicate["balance"] == 12.34, "duplicate insert overwrote durable wallet state")
    _expect(ConflictError, lambda: provider.ensure_player({**first, "type": "bot"}))
    second = _player("player-b", 5.0)
    ensured = provider.ensure_player(second)
    _require(ensured["player_id"] == "player-b", "ensure player did not create a missing deterministic row")
    provider.bootstrap_players(_players(_player("player-a", 500.0), _player("player-c", 7.0)))
    _require(provider.get_player("player-a", _empty_players)["balance"] == 12.34, "bootstrap replaced an existing wallet")
    _require(provider.get_player("player-c", _empty_players)["balance"] == 7.0, "bootstrap omitted a missing wallet")

    def update_row(row: dict) -> None:
        row["display_name"] = "Updated player"
        row["balance"] = 7.777

    updated = provider.update_player("player-b", update_row)
    _require(updated["display_name"] == "Updated player" and updated["balance"] == 7.78, "player update or cents normalization changed")
    _require(provider.get_player("missing-player", _empty_players) is None, "unknown point lookup did not return the declared miss")
    _expect(NotFoundError, lambda: provider.update_player("missing-player", lambda row: row.update(status="inactive")))
    loaded = provider.load_players(_empty_players)
    _require({row["player_id"] for row in loaded["players"]} == {"player-a", "player-b", "player-c"}, "player load omitted or duplicated rows")
    scan = provider.normalize_wallet_balances(apply=False)
    applied = provider.normalize_wallet_balances(apply=True)
    _require(scan["checked"] == 3 and scan["residue_count"] == 0 and scan["clean"] and not scan["applied"], "clean normalization scan report changed")
    _require(applied["checked"] == 3 and applied["normalized_count"] == 0 and applied["clean"] and applied["applied"], "clean normalization apply report changed")


def group_c_ledger_core(context: CaseContext) -> None:
    """C. Verify wallet arithmetic, errors, ordering, filters, and economics."""

    provider = context.provider
    provider.bootstrap_players(_players(_player("ledger-a", 20.0), _player("ledger-b", 5.0)))
    wager = provider.transact_ledger("ledger-a", -2.005, "WAGER", "slots", "round-1", {"kind": "base"})
    _require((wager["amount"], wager["balance_before"], wager["balance_after"]) == (-2.0, 20.0, 18.0), "ledger cents or balance boundaries changed")
    payout = provider.transact_ledger("ledger-a", 3.0, "PAYOUT", "slots", "round-1", {"kind": "base"})
    other = provider.transact_ledger("ledger-b", 1.0, "PAYOUT", "roulette", "round-2")
    before_failure = provider.read_ledger_recent(limit=100)
    before_balance = provider.get_player("ledger-a", _empty_players)["balance"]
    _expect(InsufficientFundsError, lambda: provider.transact_ledger("ledger-a", -100.0, "WAGER", "slots"))
    _expect(ValidationError, lambda: provider.transact_ledger("ledger-a", 90_000_000_000_000_001, "PAYOUT", "slots"))
    _require(provider.read_ledger_recent(limit=100) == before_failure, "rejected ledger transaction appended a row")
    _require(provider.get_player("ledger-a", _empty_players)["balance"] == before_balance, "rejected ledger transaction changed balance")
    all_rows = provider.read_ledger_recent(limit=100)
    _require([row["ledger_id"] for row in all_rows] == [wager["ledger_id"], payout["ledger_id"], other["ledger_id"]], "ledger append ordering changed")
    _require([row["ledger_id"] for row in provider.read_ledger_recent(limit=2)] == [payout["ledger_id"], other["ledger_id"]], "ledger limit did not select the chronological tail")
    _require([row["ledger_id"] for row in provider.read_ledger_recent("ledger-a", 10)] == [wager["ledger_id"], payout["ledger_id"]], "ledger player filter leaked or omitted rows")
    economics = provider.ledger_economics(window=100, game="slots", recent=2)
    _require(economics["games"] == [{"game": "slots", "wagered": 2.0, "returned": 3.0, "events": 2}], "ledger economics disagreed with hand calculation")
    _require([row["ledger_id"] for row in economics["recent"]] == [wager["ledger_id"], payout["ledger_id"]], "economics evidence order changed")


def group_d_sequencing(context: CaseContext) -> None:
    """D. Verify a strictly ordered, gapless public per-player ledger sequence."""

    provider = context.provider
    provider.bootstrap_players(_players(_player("sequence-player", 0.0)))
    returned = [provider.transact_ledger("sequence-player", 1.0, "SEQUENCE", "conformance", f"round-{index}") for index in range(1, 7)]
    durable = provider.read_ledger_recent("sequence-player", 100)
    _require([row["ledger_id"] for row in durable] == [row["ledger_id"] for row in returned], "sequential ledger order diverged from commit order")
    _assert_gapless_wallet_chain(durable, Decimal("0"))
    _require(provider.get_player("sequence-player", _empty_players)["balance"] == 6.0, "sequential ledger balance is incomplete")


def group_e_exactly_once(context: CaseContext) -> None:
    """E. Verify one durable action, exact replay, lookup, and changed-key conflict."""

    provider = context.provider
    provider.bootstrap_players(_players(_player("once-player", 10.0)))
    first, first_replayed = provider.transact_ledger_once("once-player", -1.25, "WAGER", "once-key", "slots", "once-round", {"selection": [1, 2, 3]})
    replay, replayed = provider.transact_ledger_once("once-player", -1.25, "WAGER", "once-key", "slots", "once-round", {"selection": [1, 2, 3]})
    _require(not first_replayed and replayed, "exactly-once applied/replay markers changed")
    first_bytes = json.dumps(first, sort_keys=True, separators=(",", ":")).encode("utf-8")
    replay_bytes = json.dumps(replay, sort_keys=True, separators=(",", ":")).encode("utf-8")
    _require(first_bytes == replay_bytes, "exact replay was not byte-equivalent")
    _expect(ConflictError, lambda: provider.transact_ledger_once("once-player", -1.25, "WAGER", "once-key", "slots", "once-round", {"selection": [9]}))
    _require(provider.find_ledger_action("once-player", "slots", "once-key") == first, "action lookup did not return the recorded event")
    _require(len(provider.read_ledger_recent("once-player", 10)) == 1, "exact replay duplicated the ledger row")
    _require(provider.get_player("once-player", _empty_players)["balance"] == 8.75, "exact replay duplicated the wallet mutation")


def group_f_history(context: CaseContext) -> None:
    """F. Verify history append order, tail limits, filters, and schema metadata."""

    provider = context.provider
    events = [_history_event(1, "slots"), _history_event(2, "roulette"), _history_event(3, "slots")]
    for event in events:
        _require(set(event) == set(HISTORY_FIELDS), "history fixture drifted from the provider contract")
        provider.append_history(event)
    recent = provider.recent_history(limit=2)
    _require([row["round_id"] for row in recent] == ["round-2", "round-3"], "history limit or append ordering changed")
    slots = provider.recent_history(limit=10, game="slots")
    _require([row["round_id"] for row in slots] == ["round-1", "round-3"], "history game filter leaked or omitted rows")
    _require(all(str(row["schema_version"]) == "1" for row in slots), "history schema version did not round-trip")
    _require(Decimal(str(slots[-1]["amount"])) == Decimal("3"), "history money value changed across storage encoding")


def _run_thread_wave(count: int, operation: Callable[[int], object]) -> list[object]:
    """Release one exact worker wave together and surface every result."""

    barrier = threading.Barrier(count)

    def invoke(index: int) -> object:
        barrier.wait(timeout=5)
        return operation(index)

    with ThreadPoolExecutor(max_workers=count) as executor:
        return list(executor.map(invoke, range(count)))


def group_g_concurrency(context: CaseContext) -> None:
    """G. Exercise threads for wallet, document, and same-key atomicity."""

    provider = context.provider
    magnitude = 8 if context.supports_true_concurrency else 4
    transaction_count = 2 * magnitude
    provider.bootstrap_players(_players(_player("concurrent-player", 0.0)))
    _run_thread_wave(transaction_count, lambda index: provider.transact_ledger("concurrent-player", 1.0, "CONCURRENT", "conformance", f"round-{index}"))
    rows = provider.read_ledger_recent("concurrent-player", transaction_count + 10)
    _require(len(rows) == transaction_count, "concurrent ledger lost or duplicated rows")
    _require(provider.get_player("concurrent-player", _empty_players)["balance"] == float(transaction_count), "concurrent ledger lost wallet updates")
    _assert_gapless_wallet_chain(rows, Decimal("0"))
    document_key = "conformance/g/counter"
    provider.write_document(document_key, {"count": 0, "seen": []})

    def update_counter(index: int) -> dict:
        def mutate(current: dict) -> dict:
            current["count"] += 1
            current["seen"].append(index)
            return current

        return provider.update_document(document_key, mutate, {"count": 0, "seen": []})

    _run_thread_wave(transaction_count, update_counter)
    document = provider.read_document(document_key, {})
    _require(document["count"] == transaction_count and sorted(document["seen"]) == list(range(transaction_count)), "concurrent document update lost a mutation")
    same_key_results = _run_thread_wave(transaction_count, lambda _index: provider.transact_ledger_once("concurrent-player", 1.0, "ONCE", "shared-key", "conformance", "shared-round", {"proof": "same"}))
    applied = [not result[1] for result in same_key_results]
    event_ids = {result[0]["ledger_id"] for result in same_key_results}
    _require(sum(applied) == 1 and len(event_ids) == 1, "concurrent same-key action did not apply exactly once")
    _require(provider.get_player("concurrent-player", _empty_players)["balance"] == float(transaction_count + 1), "same-key replay changed wallet more than once")
    final_rows = provider.read_ledger_recent("concurrent-player", transaction_count + 10)
    _require(len(final_rows) == transaction_count + 1, "same-key replay changed ledger more than once")
    _assert_gapless_wallet_chain(final_rows, Decimal("0"))


def group_h_transactions_visibility(context: CaseContext) -> None:
    """H. Verify visibility contexts and rollback after caller failures."""

    provider = context.provider
    provider.bootstrap_players(_players(_player("visibility-player", 10.0)))
    provider.write_document("conformance/h/state", {"generation": "before"})
    with provider.state_visibility_transaction() as visible_provider:
        _require(visible_provider is provider, "state visibility context yielded a foreign provider")
        _require(visible_provider.read_document("conformance/h/state", {}) == {"generation": "before"}, "visibility context hid committed state")

    def fail_document(current: dict) -> dict:
        current["generation"] = "partial"
        raise _InjectedFailure("document failure")

    _expect(_InjectedFailure, lambda: provider.update_document("conformance/h/state", fail_document, {}))
    _require(provider.read_document("conformance/h/state", {}) == {"generation": "before"}, "failed document transaction published partial state")

    def fail_reset_body() -> None:
        with provider.reset_transaction() as reset_provider:
            _require(reset_provider is provider, "reset context yielded a foreign provider")
            reset_provider.write_document("conformance/h/state", {"generation": "partial-reset"})
            reset_provider.bootstrap_players(_players(_player("partial-player", 1.0)))
            raise _InjectedFailure("reset body failure")

    _expect(_InjectedFailure, fail_reset_body)
    _require(provider.read_document("conformance/h/state", {}) == {"generation": "before"}, "failed reset exposed partial document state")
    restored_ids = {row["player_id"] for row in provider.load_players(_empty_players)["players"]}
    _require(restored_ids == {"visibility-player"}, "failed reset exposed partial wallet state")


def group_i_reset(context: CaseContext) -> None:
    """I. Verify fresh-equivalent reset state and rerun document basics."""

    provider = context.provider
    provider.bootstrap_players(_players(_player("reset-player", 5.0)))
    provider.transact_ledger("reset-player", 1.0, "RESET", "conformance", "reset-round")
    provider.append_history(_history_event(1, "slots"))
    provider.write_document("conformance/i/stale", {"stale": True})
    provider.reset()
    provider.ensure_ready()
    _require(provider.load_players(_empty_players) == _empty_players(), "reset did not restore fresh wallet state")
    _require(provider.read_ledger_recent(limit=10) == [], "reset retained mutable ledger state")
    _require(provider.recent_history(limit=10) == [], "reset retained mutable history state")
    _require(not provider.document_exists("conformance/i/stale"), "reset retained a mutable document")
    _document_basics(provider, "conformance/i/rerun")


def group_j_error_taxonomy(context: CaseContext) -> None:
    """J. Verify public domain failures use declared, secret-safe casino errors."""

    provider = context.provider
    provider.bootstrap_players(_players(_player("error-player", 1.0)))
    errors = [
        _expect(NotFoundError, lambda: provider.transact_ledger("missing-player", 1.0, "ERROR")),
        _expect(ValidationError, lambda: provider.transact_ledger("error-player", 0.0, "ERROR")),
        _expect(ValidationError, lambda: provider.transact_ledger("error-player", 90_000_000_000_000_001, "ERROR")),
        _expect(InsufficientFundsError, lambda: provider.transact_ledger("error-player", -2.0, "ERROR")),
    ]
    provider.transact_ledger_once("error-player", 0.5, "ONCE", "taxonomy-key", "conformance", "taxonomy-round", {"proof": "stable"})
    errors.append(_expect(ConflictError, lambda: provider.transact_ledger_once("error-player", 0.5, "ONCE", "taxonomy-key", "conformance", "taxonomy-round", {"proof": "credential-marker"})))
    errors.append(_expect(ValidationError, lambda: provider.find_ledger_action("error-player", "conformance", "")))
    forbidden = ("credential-marker", "password=", "postgresql://", "mysql://", "select ", "insert ", "update ", "delete from", "where ")
    for error in errors:
        _require(isinstance(error, CasinoError) and type(error).__module__ == "casino.errors", "provider-native exception escaped the public contract")
        exposed = f"{error} {getattr(error, 'details', {})}".lower()
        _require(not any(fragment in exposed for fragment in forbidden), "public storage error exposed credential, target, or query detail")


GROUPS = (
    ConformanceGroup("A", "documents", group_a_documents),
    ConformanceGroup("B", "players", group_b_players),
    ConformanceGroup("C", "ledger_core", group_c_ledger_core),
    ConformanceGroup("D", "sequencing", group_d_sequencing),
    ConformanceGroup("E", "exactly_once", group_e_exactly_once),
    ConformanceGroup("F", "history", group_f_history),
    ConformanceGroup("G", "concurrency", group_g_concurrency),
    ConformanceGroup("H", "transactions_visibility", group_h_transactions_visibility),
    ConformanceGroup("I", "reset", group_i_reset),
    ConformanceGroup("J", "error_taxonomy", group_j_error_taxonomy),
)
