"""Listener-free hostile proof for the #323 Package C process-safety checkpoint."""

# Import syntax-tree parsing for isolated structural fixtures.
import ast
# Import output redirection for the fixed command-line privacy boundary.
import contextlib
# Import in-memory text streams for exact stdout and stderr assertions.
import io
# Import JSON parsing errors for hostile serialization and manifest fixtures.
import json
# Import portable paths for the exact checkout and disposable source trees.
from pathlib import Path
# Import disposable directories for malformed and unreachable source fixtures.
import tempfile
# Import standard unit-test assertions.
import unittest
# Import bounded patching for clean-tree and failure injection.
from unittest import mock

# Import the static audit without importing Casino runtime modules.
from scripts import audit_multiprocess_safety as audit


# Build one parsed source record without importing the fixture.
def parsed_module(path: str, source: str) -> dict:
    # Return the repository-relative identity and parsed syntax tree.
    return {"path": path, "tree": ast.parse(source, filename=path)}


# Prove exhaustive structural inventory and fail-closed semantic classification.
class MultiprocessSafetyInventoryTests(unittest.TestCase):
    # Build one exact-current inventory from tracked source without requiring archive Git metadata.
    @classmethod
    def setUpClass(cls) -> None:  # Build shared exact-current structural evidence.
        # Bind the isolated Package C source tree without changing process working directory.
        cls.repo_root = Path(__file__).resolve().parents[2]
        # Supply one valid synthetic commit because release validation uses a Git-free exact-HEAD archive.
        cls.commit = "0" * 40
        # Bind provenance to the synthetic identity while retaining all source-byte analysis.
        with mock.patch.object(audit, "source_commit", return_value=cls.commit):
            # Permit both a normal checkout and the exact tracked release archive fixture.
            with mock.patch.object(audit, "require_clean_tree"):
                # Build one immutable structural packet for current-source assertions.
                cls.inventory = audit.build_inventory(cls.repo_root, cls.commit)

    # Prove all 46 registered games receive one conservative reachable persistence disposition.
    def test_all_registered_games_are_reachably_classified_and_blocked(self) -> None:
        # Read the complete governed game inventory.
        games = self.inventory["games"]
        # Pin exact deployed catalog coverage.
        self.assertEqual(len(games), audit.EXPECTED_GAME_COUNT)
        # Reject duplicate or omitted game identities.
        self.assertEqual(len({row["game_id"] for row in games}), audit.EXPECTED_GAME_COUNT)
        # Pin the exact two current persistence families.
        self.assertEqual(
            {row["state_model"] for row in games},  # Compare every current model.
            {"player_document_load_save", "shared_simple_game_load_save"},  # Pin accepted families.
        )
        # Pin the exact current family cardinalities without averaging away one game.
        self.assertEqual(
            {
                model: sum(row["state_model"] == model for row in games)  # Count one model.
                for model in {"player_document_load_save", "shared_simple_game_load_save"}  # Cover both models.
            },
            {"player_document_load_save": 35, "shared_simple_game_load_save": 11},  # Pin current counts.
        )
        # Require bounded live call-graph evidence for every game.
        self.assertTrue(all(row["reachable_definitions"] > 0 for row in games))
        # Refuse second-worker authorization for every game.
        self.assertTrue(all(row["multiworker_status"] == "blocked" for row in games))
        # Pin the missing cross-process state-and-money boundary rationale.
        self.assertTrue(
            all(  # Require one exact reason across the catalog.
                row["reason"] == "state_and_money_not_committed_by_one_cross_process_boundary"  # Match reason.
                for row in games  # Inspect every registered game.
            )
        )

    # Prove every required control-plane surface uses live call sites rather than source markers.
    def test_required_components_are_structural_and_conservative(self) -> None:
        # Index components by stable sanitized identity.
        components = {row["component"]: row for row in self.inventory["components"]}
        # Pin the complete Package C control-plane inventory.
        self.assertEqual(
            set(components),  # Compare all component identities.
            {
                "auth_sessions",  # Include session persistence.
                "request_rate_limiter",  # Include rate-limit state.
                "operations_heartbeat",  # Include Operations state.
                "autoplay_registry",  # Include autoplay state.
                "bot_controller",  # Include bot game state.
            },
        )
        # Require the live auth paths to expose their current mixed atomic/direct writes.
        self.assertEqual(
            (  # Compare semantic model and decision together.
                components["auth_sessions"]["state_model"],  # Read current model.
                components["auth_sessions"]["multiworker_status"],  # Read current disposition.
            ),
            ("mixed_atomic_and_direct_document_writes", "blocked"),  # Pin fail-closed semantics.
        )
        # Require at least one live atomic and one live direct auth mutation.
        self.assertGreater(components["auth_sessions"]["atomic_call_sites"], 0)
        # Require the unsafe live auth path to remain explicit.
        self.assertGreater(components["auth_sessions"]["direct_write_call_sites"], 0)
        # Require all declared bot ownership rather than a Roulette sample.
        self.assertEqual(
            components["bot_controller"]["owned_games"],  # Read complete bot ownership.
            ["baccarat", "bingo", "keno", "roulette"],  # Pin every owned game.
        )
        # Require bounded reachability evidence for auth, autoplay, and bot paths.
        self.assertTrue(
            all(  # Require proof for every call-graph component.
                components[name]["reachable_definitions"] > 0  # Require a live definition.
                for name in {"auth_sessions", "autoplay_registry", "bot_controller"}  # Cover three graphs.
            )
        )
        # Require exact derived auth mutator ownership.
        self.assertEqual(
            components["auth_sessions"]["mutating_entrypoints"],  # Read published auth mutators.
            sorted(audit.AUTH_SESSION_ROOTS),  # Compare reviewed complete ownership.
        )
        # Require exact derived auth read-only ownership.
        self.assertEqual(
            components["auth_sessions"]["read_only_entrypoints"],  # Read published auth readers.
            sorted(audit.AUTH_SESSION_READ_ONLY_ROOTS),  # Compare reviewed read-only ownership.
        )
        # Require exact derived autoplay mutator ownership.
        self.assertEqual(
            components["autoplay_registry"]["mutating_entrypoints"],  # Read lifecycle mutators.
            sorted(audit.AUTOPLAY_ROOTS),  # Compare reviewed lifecycle ownership.
        )
        # Require exact derived autoplay read-only ownership.
        self.assertEqual(
            components["autoplay_registry"]["read_only_entrypoints"],  # Read lifecycle readers.
            sorted(audit.AUTOPLAY_READ_ONLY_ROOTS),  # Compare reviewed read ownership.
        )
        # Require exact derived bot mutator ownership.
        self.assertEqual(
            components["bot_controller"]["mutating_entrypoints"],  # Read bot mutators.
            sorted(audit.BOT_ROOTS),  # Compare every public bot dispatcher.
        )
        # Require no unclassified public bot read-only path.
        self.assertEqual(
            components["bot_controller"]["read_only_entrypoints"],  # Read bot readers.
            sorted(audit.BOT_READ_ONLY_ROOTS),  # Compare reviewed empty ownership.
        )
        # Refuse a second worker for every required component.
        self.assertTrue(all(row["multiworker_status"] == "blocked" for row in components.values()))

    # Prove module object discovery is name-agnostic across core, app, WSGI, and games.
    def test_module_objects_cover_public_lowercase_services_and_provider_singletons(self) -> None:
        # Index every module object by portable path and exact symbol.
        rows = {
            (row["path"], row["symbol"]): row  # Index one module object.
            for row in self.inventory["module_state"]  # Inspect complete module state.
        }
        # Pin the application router even though its public name does not end in SERVICE.
        self.assertEqual(rows[("casino/app.py", "ROUTER")]["multiworker_status"], "blocked")
        # Pin the lowercase WSGI application singleton.
        self.assertEqual(rows[("casino/wsgi.py", "application")]["multiworker_status"], "blocked")
        # Pin the reviewed settlement adapter singleton.
        self.assertEqual(
            rows[("casino/core/settlement.py", "_DEFAULT_ADAPTER")]["state_model"],  # Read adapter model.
            "stateless_settlement_adapter",  # Pin reviewed semantics.
        )
        # Resolve the six explicit game adapter instances introduced by settlement convergence.
        game_adapters = {
            (row["path"], row["symbol"])  # Preserve adapter ownership.
            for row in self.inventory["module_state"]  # Inspect complete module state.
            if row["state_model"] == "stateless_settlement_adapter"  # Select reviewed adapters.
            and row["path"].startswith("casino/games/")  # Exclude the shared default adapter.
        }
        # Pin every current explicit game adapter so additions require review.
        self.assertEqual(
            game_adapters,
            {
                ("casino/games/baccarat/api.py", "SETTLEMENT"),  # Pin Baccarat ownership.
                ("casino/games/bingo/api.py", "SETTLEMENT"),  # Pin Bingo ownership.
                ("casino/games/blackjack/api.py", "SETTLEMENT"),  # Pin Blackjack ownership.
                ("casino/games/keno/api.py", "SETTLEMENT"),  # Pin Keno ownership.
                ("casino/games/roulette/api.py", "SETTLEMENT"),  # Pin Roulette ownership.
                ("casino/games/slots/api.py", "SETTLEMENT"),  # Pin Slots ownership.
            },
        )
        # Pin both lazy provider cache symbols.
        self.assertEqual(
            {
                rows[("casino/core/storage.py", "_PROVIDER")]["state_model"],  # Read runtime provider.
                rows[("casino/core/storage.py", "_TEST_PROVIDER")]["state_model"],  # Read test provider.
            },
            {"per_process_provider_cache", "test_provider_injection"},  # Pin both reviewed models.
        )
        # Resolve all deployed game service singleton rows.
        game_services = {
            (row["path"], row["symbol"])  # Preserve service ownership.
            for row in self.inventory["module_state"]  # Inspect complete module state.
            if row["state_model"] == "game_service_singleton"  # Select constructed game services.
        }
        # Pin the four current module-owned game service objects.
        self.assertEqual(
            game_services,  # Compare all discovered game services.
            {
                ("casino/games/big_six_wheel/api.py", "SERVICE"),  # Pin Big Six service.
                ("casino/games/crown_and_anchor/api.py", "SERVICE"),  # Pin Crown service.
                ("casino/games/fan_tan/api.py", "SERVICE"),  # Pin Fan Tan service.
                ("casino/games/scratch_cards/api.py", "SERVICE"),  # Pin Scratch service.
            },
        )

    # Prove instance-held locks, counters, cursors, caches, and pool state are not invisible.
    def test_instance_state_covers_mysql_security_operations_and_storage(self) -> None:
        # Index mutable instance surfaces by portable class identity.
        rows = {
            (row["path"], row["class"], row["attribute"]): row  # Index one instance surface.
            for row in self.inventory["instance_state"]  # Inspect complete instance state.
        }
        # Pin the process-bound MySQL condition, idle set, metrics, and cursor inventory.
        for key in {
            ("casino/core/mysql_pool.py", "MySQLConnectionPool", "_condition"),  # Pin pool condition.
            ("casino/core/mysql_pool.py", "MySQLConnectionPool", "_idle"),  # Pin idle connections.
            ("casino/core/mysql_pool.py", "MySQLConnectionPool", "_metrics"),  # Pin pool metrics.
            ("casino/core/mysql_pool.py", "MySQLConnectionLease", "_cursors"),  # Pin lease cursors.
        }:  # Inspect each required pool surface.
            # Require each process-owned pool surface to be present and explicitly compatible.
            self.assertEqual(rows[key]["multiworker_status"], "compatible")
        # Require the rate-limiter registry and lock to remain visible blockers.
        for attribute in {"clients", "lock"}:
            # Pin each exact security surface.
            self.assertEqual(
                rows[("casino/core/security.py", "RateLimiter", attribute)]["multiworker_status"],  # Read status.
                "blocked",  # Pin conservative decision.
            )
        # Require Operations heartbeat value and synchronization to remain visible blockers.
        for attribute in {"_heartbeat_lock", "_last_successful_heartbeat_at"}:
            # Pin each exact Operations surface.
            self.assertEqual(
                rows[("casino/operations/service.py", "OperationsProbeService", attribute)][  # Read row.
                    "multiworker_status"  # Read exact disposition.
                ],
                "blocked",  # Pin conservative decision.
            )

    # Prove arbitrary public, lowercase, registry, and conditional module objects fail closed.
    def test_unknown_module_objects_are_name_agnostic_and_conditional(self) -> None:
        # Parse a hostile runtime with no recognized singleton naming convention.
        module = parsed_module(
            "casino/runtime.py",  # Assign one portable hostile identity.
            """
REGISTRY = {}
COUNTER = 0
runtime = MutableCoordinator()
if ENABLED:
    conditional = MutableCoordinator()
PUBLIC_OBJECT = MutableCoordinator()

def bump():
    global COUNTER
    COUNTER += 1
""",
        )
        # Inventory the hostile module without importing it.
        rows = audit._module_state_inventory([module], set())
        # Index rows by exact hostile symbol.
        by_symbol = {row["symbol"]: row for row in rows}
        # Require every arbitrary declaration to be discovered.
        self.assertEqual(
            set(by_symbol),  # Compare every discovered hostile symbol.
            {"REGISTRY", "COUNTER", "runtime", "conditional", "PUBLIC_OBJECT"},  # Pin objects and scalar.
        )
        # Refuse compatibility for every unknown object or unlocked registry.
        self.assertTrue(all(row["multiworker_status"] == "blocked" for row in rows))
        # Pin conditional and lowercase declarations to the conservative singleton model.
        self.assertEqual(by_symbol["conditional"]["state_model"], "process_local_singleton_or_cache")
        # Pin the unmutated registry name to mutable module state.
        self.assertEqual(by_symbol["REGISTRY"]["state_model"], "mutable_module_container")
        # Pin a mutated scalar that would otherwise look immutable at initialization.
        self.assertEqual(by_symbol["COUNTER"]["state_model"], "mutated_module_scalar_or_object")
        # Refuse a second worker for the process-local scalar.
        self.assertEqual(by_symbol["COUNTER"]["multiworker_status"], "blocked")

    # Prove every new public state mutator fails root reconciliation until explicitly reviewed.
    def test_unlisted_public_state_mutator_fails_closed(self) -> None:
        # Parse declared mutation/read paths plus one hostile omitted public mutator.
        module = parsed_module(
            "casino/core/fixture.py",  # Assign one portable component identity.
            """
def declared_mutator():
    update_json(SESSIONS_PATH, mutate)

def declared_reader():
    read_json(SESSIONS_PATH, {})

def strict_reader():
    read_json_strict(SESSIONS_PATH, {}, "fixed")

def new_live_mutator():
    write_json(SESSIONS_PATH, snapshot)

def _private_dead_helper():
    write_json(SESSIONS_PATH, dead_snapshot)
""",
        )
        # Derive every public entrypoint that reaches the owned session document.
        discovered = audit._public_state_entrypoints(
            [module],  # Restrict discovery to the hostile component.
            read_calls={"read_json", "read_json_strict"},  # Classify ordinary and strict reads.
            mutation_calls={"update_json", "update_json_strict", "write_json"},  # Classify mutations.
            document_symbol="SESSIONS_PATH",  # Require exact owned document calls.
        )
        # Require the hostile public mutator to be visible while the private dead helper is excluded.
        self.assertEqual(
            discovered,  # Compare complete structural discovery.
            {
                "mutating": ["declared_mutator", "new_live_mutator"],  # Pin both public mutators.
                "read_only": ["declared_reader", "strict_reader"],  # Pin both public readers.
            },
        )
        # Reject a declaration that omits the newly discovered public mutator.
        with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "^entrypoint inventory unavailable$"):
            # Reconcile against an intentionally stale mutator set.
            audit._reconcile_state_entrypoints(  # Reconcile the exact complete disposition.
                discovered,  # Supply structural discovery.
                {"declared_mutator"},  # Omit the hostile live mutator.
                {"declared_reader", "strict_reader"},  # Preserve exact read-only dispositions.
            )
        # Accept only an exact complete disposition.
        self.assertEqual(
            audit._reconcile_state_entrypoints(
                discovered,  # Supply structural discovery.
                {"declared_mutator", "new_live_mutator"},  # Declare every public mutator.
                {"declared_reader", "strict_reader"},  # Declare every public reader.
            ),
            discovered,  # Require deterministic reconciled evidence.
        )

    # Prove unreachable synchronous and asynchronous helpers cannot forge live call evidence.
    def test_reachable_calls_exclude_dead_helpers_comments_and_false_branches(self) -> None:
        # Parse one live atomic path plus multiple marker-only and unreachable direct writes.
        module = parsed_module(
            "casino/core/fixture.py",  # Assign one portable fixture identity.
            '''
def live_entry():
    """write_json(SESSIONS_PATH, leaked_marker)"""
    marker = "write_json(SESSIONS_PATH, leaked_marker)"
    update_json(SESSIONS_PATH, mutate)
    if False:
        write_json(SESSIONS_PATH, leaked_false_branch)

def dead_helper():
    write_json(SESSIONS_PATH, leaked_dead_helper)

async def dead_async_helper():
    write_json(SESSIONS_PATH, leaked_dead_async)
''',
        )
        # Traverse only the declared live entrypoint.
        reachable = audit._reachable_facts([module], {"live_entry"})
        # Count only executable document calls reachable from that entrypoint.
        counts = audit._document_call_counts(reachable["calls"], "SESSIONS_PATH")
        # Prove every dead or textual marker is excluded.
        self.assertEqual(counts, {"atomic": 1, "read": 0, "write": 0})
        # Permit compatibility only for the reachable atomic-only fixture.
        self.assertEqual(audit._document_semantics(counts), ("provider_atomic_document", "compatible"))
        # Pin the one reachable definition rather than all three declared helpers.
        self.assertEqual(reachable["definition_count"], 1)

    # Prove a reachable safe marker cannot mask a parallel reachable unsafe path.
    def test_mixed_reachable_document_paths_are_blocked(self) -> None:
        # Parse one entrypoint with both provider-atomic and direct whole-document mutation.
        module = parsed_module(
            "casino/core/fixture.py",  # Assign one portable fixture identity.
            """
def live_entry():
    update_json(SESSIONS_PATH, mutate)
    write_json(SESSIONS_PATH, snapshot)
""",
        )
        # Traverse the one exact live entrypoint.
        reachable = audit._reachable_facts([module], {"live_entry"})
        # Count its two reachable document mutation families.
        counts = audit._document_call_counts(reachable["calls"], "SESSIONS_PATH")
        # Pin one exact safe and one exact unsafe call site.
        self.assertEqual(counts, {"atomic": 1, "read": 0, "write": 1})
        # Refuse compatibility for the mixed live path.
        self.assertEqual(
            audit._document_semantics(counts),  # Read semantic disposition.
            ("mixed_atomic_and_direct_document_writes", "blocked"),  # Pin mixed-path blocker.
        )

    # Prove game classification follows reachable registration paths and rejects dead-marker models.
    def test_game_semantics_use_reachable_registration_paths(self) -> None:
        # Parse one live player-document path plus a dead SimpleWagerGame helper.
        module = parsed_module(
            "casino/games/fixture/api.py",  # Assign one portable game identity.
            """
def register():
    live_handler()

def live_handler():
    state = load_player_game_state("fixture", "player")
    save_player_game_state("fixture", "player", state)

def dead_helper():
    SimpleWagerGame()
""",
        )
        # Classify the fixture through the real per-game semantic boundary.
        rows = audit._game_inventory(
            [{"game_id": "fixture", "backend": "casino.games.fixture.api"}],  # Define governed fixture.
            [module],  # Supply its bounded source.
        )
        # Require the dead helper not to create an overlapping persistence model.
        self.assertEqual(rows[0]["state_model"], "player_document_load_save")
        # Prove only registration and its called live handler are reachable.
        self.assertEqual(rows[0]["reachable_definitions"], 2)
        # Parse a marker-only fixture whose persistence call exists only in an uncalled helper.
        dead_only = parsed_module(
            "casino/games/fixture/api.py",  # Assign the same portable game identity.
            """
def register():
    return None

def dead_helper():
    load_player_game_state("fixture", "player")
    save_player_game_state("fixture", "player", {})
""",
        )
        # Reject the fixture because no live persistence family is reachable.
        with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "game inventory unavailable"):
            # Attempt classification through the exact registration root.
            audit._game_inventory(
                [{"game_id": "fixture", "backend": "casino.games.fixture.api"}],  # Define governed fixture.
                [dead_only],  # Supply marker-only source.
            )

    # Prove tracked and untracked dirt independently block provenance before source reads.
    def test_clean_tree_guard_rejects_tracked_and_untracked_changes(self) -> None:
        # Exercise both porcelain forms through the sanitized Git seam.
        for dirty_status in (" M casino/runtime.py\n", "?? casino/new_runtime.py\n"):
            # Replace only the Git result with the hostile dirty-tree marker.
            with mock.patch.object(audit, "_git", return_value=dirty_status):
                # Require the same fixed value-free cleanliness error.
                with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "^analyzed tree is not clean$"):
                    # Inspect the disposable repository identity.
                    audit.require_clean_tree(Path("ignored"))
        # Prove an empty porcelain result passes without source-path output.
        with mock.patch.object(audit, "_git", return_value=""):
            # Run the exact clean-tree boundary.
            audit.require_clean_tree(Path("ignored"))

    # Prove malformed source, malformed manifests, and unreadable files use fixed internal errors.
    def test_source_and_manifest_failures_are_value_free(self) -> None:
        # Create one minimal repository-shaped disposable tree.
        with tempfile.TemporaryDirectory() as temporary_directory:
            # Resolve the disposable root.
            root = Path(temporary_directory)
            # Create the required source and descriptor directories.
            for directory in ("casino", "scripts", "modules"):
                # Materialize one exact repository directory.
                (root / directory).mkdir()
            # Write one valid audit placeholder.
            (root / "scripts" / "audit_multiprocess_safety.py").write_text("VALUE = 1\n", encoding="utf-8")
            # Write one valid descriptor placeholder.
            (root / "modules" / "fixture.json").write_text('{"name":"fixture"}\n', encoding="utf-8")
            # Write malformed production Python containing a sentinel path-like value.
            (root / "casino" / "fixture.py").write_text("def SECRET_C:\\\\sentinel(:\n", encoding="utf-8")
            # Reject malformed source without echoing the syntax or path.
            with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "^source inventory unavailable$"):
                # Parse the disposable source inventory.
                audit._source_records(root)
            # Replace the production source with valid syntax.
            (root / "casino" / "fixture.py").write_text("VALUE = 1\n", encoding="utf-8")
            # Replace the descriptor with malformed JSON containing a sentinel.
            (root / "modules" / "fixture.json").write_text('{"SECRET":"C:\\\\sentinel"', encoding="utf-8")
            # Reject malformed JSON without echoing its content.
            with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "^manifest inventory unavailable$"):
                # Parse the disposable manifest inventory.
                audit._source_records(root)
        # Inject an unreadable source failure carrying a secret path.
        with mock.patch.object(Path, "read_bytes", side_effect=OSError("C:\\secret\\source.py")):
            # Require the same fixed source error.
            with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "^source inventory unavailable$"):
                # Read one hostile path through the sanitized file seam.
                audit._read_bytes(Path("C:\\secret\\source.py"))

    # Prove the standalone boundary emits no traceback, path, content, or exception text.
    def test_cli_failures_are_fixed_and_sanitized(self) -> None:
        # Exercise representative parsing, encoding, serialization, and file-system failures.
        failures = (
            json.JSONDecodeError("SECRET_BODY", "SECRET_DOCUMENT", 0),  # Inject malformed JSON.
            UnicodeDecodeError("utf-8", b"SECRET_BYTES", 0, 1, "SECRET_REASON"),  # Inject bad bytes.
            SyntaxError("SECRET_SOURCE", ("C:\\secret\\source.py", 7, 4, "SECRET_LINE")),  # Inject syntax.
            OSError("C:\\secret\\unreadable.py"),  # Inject unreadable source.
        )
        # Verify every internal failure collapses to the exact CLI contract.
        for failure in failures:
            # Capture stdout and stderr without touching the real console.
            stdout, stderr = io.StringIO(), io.StringIO()
            # Inject the hostile failure before evidence exists.
            with mock.patch.object(audit, "build_inventory", side_effect=failure):
                # Redirect both streams around the standalone entrypoint.
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    # Run one sanitized CLI attempt.
                    status = audit.main()
            # Require one fixed failure status.
            self.assertEqual(status, 1)
            # Require no partial evidence.
            self.assertEqual(stdout.getvalue(), "")
            # Require only the fixed value-free error line.
            self.assertEqual(stderr.getvalue(), audit.CLI_FAILURE_MESSAGE + "\n")
            # Reject exception details and traceback text.
            self.assertNotIn("SECRET", stderr.getvalue())
            # Reject absolute-path vocabulary.
            self.assertNotIn("C:\\", stderr.getvalue())
            # Reject traceback framing.
            self.assertNotIn("Traceback", stderr.getvalue())
        # Capture a serialization failure after a structurally valid build.
        stdout, stderr = io.StringIO(), io.StringIO()
        # Return an inert inventory and fail only deterministic JSON rendering.
        with mock.patch.object(audit, "build_inventory", return_value={"safe": True}):
            # Inject a value-bearing serializer failure.
            with mock.patch.object(audit.json, "dumps", side_effect=ValueError("SECRET_RENDER")):
                # Redirect both streams around the standalone entrypoint.
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    # Run the serialization failure path.
                    status = audit.main()
        # Require the same fixed failure status.
        self.assertEqual(status, 1)
        # Require no partial evidence.
        self.assertEqual(stdout.getvalue(), "")
        # Require the same fixed stderr contract.
        self.assertEqual(stderr.getvalue(), audit.CLI_FAILURE_MESSAGE + "\n")

    # Prove explicit provenance cannot diverge from checkout HEAD.
    def test_explicit_source_commit_is_exact_and_checkout_bound(self) -> None:
        # Reject an abbreviated source identity.
        with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "source provenance unavailable"):
            # Attempt evidence construction with an abbreviated commit.
            audit.build_inventory(self.repo_root, self.commit[:12])
        # Reject non-string caller provenance without coercion.
        with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "source provenance unavailable"):
            # Attempt evidence construction with a numeric commit.
            audit.build_inventory(self.repo_root, 1)
        # Construct a different syntactically valid source identity.
        mismatch = "0" * 40 if self.commit != "0" * 40 else "1" * 40
        # Reject a full caller identity that does not equal checkout HEAD.
        with self.assertRaisesRegex(audit.MultiprocessSafetyAuditError, "source provenance unavailable"):
            # Attempt evidence construction with the mismatched identity.
            audit.build_inventory(self.repo_root, mismatch)

    # Prove evidence is recursively sanitized and exactly reconciled.
    def test_evidence_is_relative_sanitized_and_reconciled(self) -> None:
        # Serialize the exact structural packet.
        rendered = json.dumps(self.inventory, sort_keys=True)
        # Reject the absolute checkout path.
        self.assertNotIn(str(self.repo_root), rendered)
        # Reject common secret, host, and player identity fields.
        for forbidden in ("password", "token", "cookie", "email", "player_id", "host"):
            # Assert forbidden field vocabulary is absent.
            self.assertNotIn(f'"{forbidden}"', rendered.lower())
        # Require exact checkout provenance.
        self.assertEqual(self.inventory["source_commit"], self.commit)
        # Require a complete SHA-256 digest for every analyzed source and manifest byte.
        self.assertRegex(self.inventory["analyzed_tree_sha256"], r"^[0-9a-f]{64}$")
        # Keep the checkpoint explicitly non-authorizing.
        self.assertEqual(self.inventory["decision"], "second_worker_blocked")
        # Read the compact summary.
        summary = self.inventory["summary"]
        # Reconcile every evidence family count.
        self.assertEqual(summary["catalog_game_count"], len(self.inventory["games"]))
        # Reconcile module-state count.
        self.assertEqual(summary["module_state_count"], len(self.inventory["module_state"]))
        # Reconcile instance-state count.
        self.assertEqual(summary["instance_state_count"], len(self.inventory["instance_state"]))
        # Reconcile component count.
        self.assertEqual(summary["component_count"], len(self.inventory["components"]))
        # Recompute detailed blocker rows.
        detailed = (
            self.inventory["module_state"]  # Include module objects.
            + self.inventory["instance_state"]  # Include instance surfaces.
            + self.inventory["components"]  # Include control-plane surfaces.
            + self.inventory["games"]  # Include every game.
        )
        # Require the summary blocker count to equal exact detail.
        self.assertEqual(
            summary["blocker_count"],  # Read published blocker count.
            sum(row["multiworker_status"] == "blocked" for row in detailed),  # Recompute detail.
        )
        # Require the summary compatible count to equal exact detail.
        self.assertEqual(
            summary["compatible_count"],  # Read published compatible count.
            sum(row["multiworker_status"] == "compatible" for row in detailed),  # Recompute detail.
        )


# Run the focused suite when invoked directly.
if __name__ == "__main__":
    # Delegate reporting and exit behavior to unittest.
    unittest.main()
