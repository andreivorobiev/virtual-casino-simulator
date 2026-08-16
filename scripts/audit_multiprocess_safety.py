# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Build a fail-closed Package C inventory before any second Gunicorn worker."""

# Import syntax-tree parsing for structural proof without importing Casino runtime modules.
import ast
# Import hashing for an exact digest of every analyzed source and manifest byte.
import hashlib
# Import JSON parsing and sanitized evidence rendering.
import json
# Import regular expressions for exact source identities and mutable-state names.
import re
# Import bounded Git execution for checkout provenance and cleanliness.
import subprocess
# Import fixed stderr/stdout handling for the standalone failure boundary.
import sys
# Import portable repository-relative paths.
from pathlib import Path

# Version the structural evidence independently from runtime and release artifacts.
SCHEMA = "multiprocess-safety-inventory/v2"
# Pin the deployed catalog cardinality so additions require an explicit new disposition.
EXPECTED_GAME_COUNT = 46
# Accept only complete lowercase Git object identities.
SOURCE_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
# Recognize synchronization constructors without executing their modules.
LOCK_FACTORY_NAMES = {"Lock", "RLock", "Semaphore", "BoundedSemaphore", "Event", "Condition"}
# Recognize mutable container constructors used by module and instance registries.
MUTABLE_FACTORY_NAMES = {"dict", "list", "set", "defaultdict", "deque", "OrderedDict", "Queue", "LifoQueue"}
# Recognize methods that mutate a named container in place.
MUTATING_METHOD_NAMES = {
    "add",  # Recognize set insertion.
    "append",  # Recognize sequence tail insertion.
    "clear",  # Recognize complete container removal.
    "discard",  # Recognize conditional set removal.
    "extend",  # Recognize sequence bulk insertion.
    "insert",  # Recognize positioned sequence insertion.
    "pop",  # Recognize container removal.
    "popitem",  # Recognize mapping removal.
    "remove",  # Recognize value removal.
    "setdefault",  # Recognize conditional mapping insertion.
    "sort",  # Recognize in-place sequence reordering.
    "update",  # Recognize mapping or set bulk mutation.
}
# Keep only these known module singleton factories compatible with one-process ownership.
COMPATIBLE_SINGLETON_FACTORIES = {"SystemRandom"}
# Treat these constructor/accessor results as immutable module values rather than mutable singletons.
IMMUTABLE_MODULE_FACTORIES = {
    "Decimal",  # Preserve fixed decimal values.
    "MappingProxyType",  # Preserve explicitly read-only mappings.
    "Path",  # Preserve immutable path values.
    "compile",  # Preserve compiled regular-expression or code values.
    "float",  # Preserve scalar floating-point values.
    "frozenset",  # Preserve immutable set values.
    "getenv",  # Preserve scalar environment configuration snapshots.
    "int",  # Preserve scalar integer values.
    "join",  # Preserve constructed immutable strings or paths.
    "range",  # Preserve immutable range values.
    "str",  # Preserve scalar string values.
    "tuple",  # Preserve immutable tuple values.
}
# Classify established core module locks with their reviewed process semantics.
KNOWN_CORE_LOCKS = {
    "casino/core/autoplay.py": ("autoplay_registry", "blocked"),  # Keep autoplay process-local.
    "casino/core/simple_game.py": ("simple_game_settlement", "blocked"),  # Keep game locks process-local.
    "casino/core/state_store.py": ("provider_document_boundary", "compatible"),  # Preserve provider serialization.
    "casino/core/storage.py": ("provider_factory_cache", "compatible"),  # Preserve per-process factory locking.
}
# Classify exact core singleton/cache symbols whose per-process ownership is intentional.
KNOWN_CORE_SINGLETONS = {
    ("casino/core/settlement.py", "_DEFAULT_ADAPTER"): ("stateless_settlement_adapter", "compatible"),  # Bind adapter.
    ("casino/games/baccarat/api.py", "SETTLEMENT"): ("stateless_settlement_adapter", "compatible"),  # Bind Baccarat adapter.
    ("casino/games/bingo/api.py", "SETTLEMENT"): ("stateless_settlement_adapter", "compatible"),  # Bind Bingo adapter.
    ("casino/games/blackjack/api.py", "SETTLEMENT"): ("stateless_settlement_adapter", "compatible"),  # Bind Blackjack adapter.
    ("casino/games/keno/api.py", "SETTLEMENT"): ("stateless_settlement_adapter", "compatible"),  # Bind Keno adapter.
    ("casino/games/roulette/api.py", "SETTLEMENT"): ("stateless_settlement_adapter", "compatible"),  # Bind Roulette adapter.
    ("casino/games/slots/api.py", "SETTLEMENT"): ("stateless_settlement_adapter", "compatible"),  # Bind Slots adapter.
    ("casino/core/storage.py", "_PROVIDER"): ("per_process_provider_cache", "compatible"),  # Bind runtime provider.
    ("casino/core/storage.py", "_TEST_PROVIDER"): ("test_provider_injection", "compatible"),  # Bind test provider.
}
# Bound session proof to exact public/live mutation and compatibility entrypoints.
AUTH_SESSION_ROOTS = {
    "accept_terms",  # Include terms acceptance mutation.
    "authenticate_headers",  # Include header authentication expiry mutation.
    "authenticate_token",  # Include token lookup and expiry mutation.
    "bootstrap_admin_from_env",  # Include bootstrap session mutation.
    "consume_guest_action",  # Include guest allowance mutation.
    "create_guest",  # Include guest-session creation.
    "create_session",  # Include authenticated-session creation.
    "end_guest_trial",  # Include guest-session closure.
    "expire_overdue_guests",  # Include overdue guest closure.
    "import_auth_state",  # Include compatibility-state import.
    "login",  # Include login session creation.
    "logout",  # Include one-session revocation.
    "mark_guest_departed",  # Include guest departure state.
    "revoke_admin_session_for_user",  # Include one administrative revocation.
    "revoke_all_admin_sessions_for_user",  # Include bulk administrative revocation.
    "revoke_session_by_id",  # Include the owner-confirmed single-session revocation path.
    "revoke_sessions_for_user",  # Include user session revocation.
    "revoke_sessions_for_user_method",  # Include method-scoped revocation.
    "rotate_mobile_session",  # Include atomic native bearer-and-CSRF replacement.
    "save_sessions",  # Include direct compatibility snapshot writes.
    "set_user_password",  # Include password-driven session mutation.
    "update_user_by_id",  # Include user-driven session mutation.
}
# Declare every public session entrypoint that only reads the owned session document.
AUTH_SESSION_READ_ONLY_ROOTS = {
    "csrf_token_for_session_cookie",  # Include CSRF derivation reads.
    "export_auth_state",  # Include compatibility-state reads.
    "list_admin_sessions_for_user",  # Include strict administrative session reads.
    "load_sessions",  # Include direct compatibility snapshot reads.
    "online_user_count",  # Include the bounded presence read over current sessions.
}
# Bound autoplay proof to every public lifecycle entrypoint.
AUTOPLAY_ROOTS = {
    "complete",  # Include terminal session completion.
    "finish_stop",  # Include stop completion.
    "save_state",  # Include direct registry writes.
    "start",  # Include session creation.
    "stop",  # Include one-session stop.
    "stop_all",  # Include global stop.
    "stop_for_player",  # Include player-owned stop.
    "tick",  # Include one autoplay action.
    "update",  # Include session update.
}
# Declare every public autoplay entrypoint that only reads the registry document.
AUTOPLAY_READ_ONLY_ROOTS = {
    "get_session",  # Include one-session reads.
    "list_sessions",  # Include registry enumeration.
    "load_state",  # Include direct registry reads.
}
# Bound bot proof to every public state-mutating game dispatcher.
BOT_ROOTS = {
    "play_baccarat_round",  # Include direct Baccarat bot actions.
    "play_bingo_round",  # Include direct Bingo bot actions.
    "play_keno_round",  # Include direct Keno bot actions.
    "play_roulette_round",  # Include direct Roulette bot actions.
    "play_round",  # Include the catalog dispatcher.
}
# Declare the empty set of public bot state readers.
BOT_READ_ONLY_ROOTS: set[str] = set()
# Name the only fixed error allowed to escape the standalone CLI.
CLI_FAILURE_MESSAGE = "multiprocess safety audit failed"


# Represent every internal inventory defect with a value-free exception type.
class MultiprocessSafetyAuditError(RuntimeError):
    """Report incomplete, dirty, malformed, or unclassified source evidence."""


# Return the leaf identifier from a direct or qualified callable expression.
def _call_leaf_name(node: ast.AST) -> str:
    # Preserve a direct function or class identifier.
    if isinstance(node, ast.Name):
        # Return the exact static name.
        return node.id
    # Preserve the final attribute from a qualified call.
    if isinstance(node, ast.Attribute):
        # Return only the static attribute name.
        return node.attr
    # Return no identity for dynamic expressions.
    return ""


# Return the base name from a direct object expression such as registry.update().
def _base_name(node: ast.AST) -> str:
    # Preserve a direct name.
    if isinstance(node, ast.Name):
        # Return its static identifier.
        return node.id
    # Follow attributes and subscripts to their root object.
    if isinstance(node, (ast.Attribute, ast.Subscript)):
        # Recurse through the owned value expression.
        return _base_name(node.value)
    # Return no identity for dynamic roots.
    return ""


# Return whether an AST condition is the literal unreachable value False.
def _literal_false(node: ast.AST) -> bool:
    # Recognize only the exact false constant without evaluating arbitrary code.
    return isinstance(node, ast.Constant) and node.value is False


# Visit executable syntax while skipping literal-false branches.
class ExecutableVisitor(ast.NodeVisitor):
    """Collect structural facts while excluding explicit dead-code branches."""

    # Skip literal-false bodies while retaining their reachable else branches.
    def visit_If(self, node: ast.If) -> None:
        # Visit only the alternate branch when the condition is exactly false.
        if _literal_false(node.test):
            # Visit each reachable alternate statement.
            for statement in node.orelse:
                # Continue normal structural traversal.
                self.visit(statement)
            # Stop before visiting the unreachable body.
            return
        # Use normal traversal for dynamic conditions.
        self.generic_visit(node)


# Collect assignments executed directly at module initialization, including conditional branches.
class ModuleAssignmentCollector(ExecutableVisitor):
    """Collect name-agnostic module objects without entering function or class bodies."""

    # Initialize one empty declaration list.
    def __init__(self) -> None:
        # Retain direct module targets and assigned AST values.
        self.assignments: list[tuple[str, ast.AST | None]] = []

    # Do not treat function-local assignments as module initialization.
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Stop at the function boundary.
        return

    # Treat asynchronous functions identically.
    visit_AsyncFunctionDef = visit_FunctionDef

    # Do not treat class-body assignments as module globals.
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Stop at the class boundary.
        return

    # Record one ordinary module assignment.
    def visit_Assign(self, node: ast.Assign) -> None:
        # Retain every direct module-name target.
        for target in node.targets:
            # Record only static direct names.
            if isinstance(target, ast.Name):
                # Preserve the exact assigned AST value.
                self.assignments.append((target.id, node.value))
        # Traverse the value only for conditional expression structure.
        self.visit(node.value)

    # Record one annotated module assignment.
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        # Retain one direct annotated module name.
        if isinstance(node.target, ast.Name):
            # Preserve the exact assigned AST value.
            self.assignments.append((node.target.id, node.value))
        # Traverse an assigned value when present.
        if node.value is not None:
            # Continue through the value expression.
            self.visit(node.value)


# Scan one reachable body without entering unreferenced nested declarations.
class ReachableBodyCollector(ExecutableVisitor):
    """Collect calls, names, and decorated callbacks from one reachable body."""

    # Initialize structural reachable facts.
    def __init__(self) -> None:
        # Retain reachable call records.
        self.calls: list[dict] = []
        # Retain referenced static names for injected defaults and call-graph expansion.
        self.names: set[str] = set()
        # Retain decorated nested callback definitions registered by a live entrypoint.
        self.callbacks: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    # Record static name references.
    def visit_Name(self, node: ast.Name) -> None:
        # Add the static reference identity.
        self.names.add(node.id)

    # Record one reachable call.
    def visit_Call(self, node: ast.Call) -> None:
        # Resolve the static callable leaf.
        name = _call_leaf_name(node.func)
        # Normalize the optional first argument.
        first_argument = node.args[0] if node.args else None
        # Retain the structural call record.
        self.calls.append({"name": name, "first_argument": first_argument})
        # Retain the callable name for local call-graph expansion.
        if name:
            # Add the static call identity.
            self.names.add(name)
        # Continue through arguments and nested expressions.
        self.generic_visit(node)

    # Exclude unreferenced nested functions unless decorators register them as callbacks.
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Retain decorated nested handlers owned by a reachable registration function.
        if node.decorator_list:
            # Queue the callback body for reachable traversal.
            self.callbacks.append(node)
        # Stop before visiting an uncalled nested body.
        return

    # Treat asynchronous nested functions identically.
    visit_AsyncFunctionDef = visit_FunctionDef

    # Exclude nested class bodies until their constructor is reached explicitly.
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Stop at the unreferenced class boundary.
        return


# Collect module-name mutation outside module initialization.
class ModuleMutationCollector(ExecutableVisitor):
    """Find reassignment and in-place mutation of module-owned names."""

    # Initialize one empty mutation counter.
    def __init__(self) -> None:
        # Count mutation sites by static module symbol.
        self.counts: dict[str, int] = {}
        # Track whether traversal is inside a function or class body.
        self.scope_depth = 0

    # Increment one static module-name mutation count.
    def _record(self, name: str) -> None:
        # Count only non-empty static names.
        if name:
            # Add one mutation site to the stable symbol counter.
            self.counts[name] = self.counts.get(name, 0) + 1

    # Enter a function where global assignments represent runtime mutation.
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Mark nested scope before visiting the function body.
        self.scope_depth += 1
        # Visit executable statements inside the function.
        self.generic_visit(node)
        # Restore the parent scope after traversal.
        self.scope_depth -= 1

    # Treat asynchronous functions identically.
    visit_AsyncFunctionDef = visit_FunctionDef

    # Enter a class where method assignments also occur below module scope.
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Mark nested scope before visiting methods.
        self.scope_depth += 1
        # Visit executable class and method statements.
        self.generic_visit(node)
        # Restore the parent scope after traversal.
        self.scope_depth -= 1

    # Record assignments to names explicitly declared global.
    def visit_Global(self, node: ast.Global) -> None:
        # Record every runtime-owned global symbol.
        for name in node.names:
            # Count the explicit global mutation capability.
            self._record(name)

    # Record direct and subscript assignments below module scope.
    def visit_Assign(self, node: ast.Assign) -> None:
        # Inspect only runtime assignments rather than module declarations.
        if self.scope_depth:
            # Inspect every assignment target.
            for target in node.targets:
                # Record direct names and container-root mutations.
                self._record(_base_name(target))
        # Continue through nested expressions.
        self.generic_visit(node)

    # Record annotated runtime assignments.
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        # Inspect only runtime assignments rather than module declarations.
        if self.scope_depth:
            # Record the annotated target root.
            self._record(_base_name(node.target))
        # Continue through the annotation and value.
        self.generic_visit(node)

    # Record augmented runtime assignments such as counter += 1.
    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # Inspect only runtime-owned state.
        if self.scope_depth:
            # Record the mutated target root.
            self._record(_base_name(node.target))
        # Continue through the assigned expression.
        self.generic_visit(node)

    # Record mutating method calls on static module names.
    def visit_Call(self, node: ast.Call) -> None:
        # Require one recognized mutating attribute call.
        if self.scope_depth and isinstance(node.func, ast.Attribute) and node.func.attr in MUTATING_METHOD_NAMES:
            # Record the root object receiving the mutation.
            self._record(_base_name(node.func.value))
        # Continue through nested calls.
        self.generic_visit(node)


# Collect initialized and subsequently mutated instance state by class.
class InstanceStateCollector(ExecutableVisitor):
    """Inventory instance locks, containers, counters, and mutable state."""

    # Initialize class and method context.
    def __init__(self) -> None:
        # Track the current class identity.
        self.class_name = ""
        # Track the current method identity.
        self.method_name = ""
        # Retain initializer factories by class and attribute.
        self.initializers: dict[tuple[str, str], str] = {}
        # Retain runtime mutation counts by class and attribute.
        self.mutations: dict[tuple[str, str], int] = {}

    # Enter one class with isolated method context.
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Preserve the parent class identity for nested declarations.
        previous_class = self.class_name
        # Set the current static class identity.
        self.class_name = node.name
        # Visit class methods and nested classes.
        self.generic_visit(node)
        # Restore the parent class identity.
        self.class_name = previous_class

    # Enter one method with its static name.
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Preserve the parent method identity.
        previous_method = self.method_name
        # Set the current method identity only inside a class.
        self.method_name = node.name if self.class_name else ""
        # Visit method statements.
        self.generic_visit(node)
        # Restore the parent method identity.
        self.method_name = previous_method

    # Treat asynchronous methods identically.
    visit_AsyncFunctionDef = visit_FunctionDef

    # Resolve a direct self.attribute assignment target.
    def _self_attribute(self, node: ast.AST) -> str:
        # Require one direct self-owned attribute.
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
            # Return the static attribute identity.
            return node.attr
        # Follow a subscript to its owning self attribute.
        if isinstance(node, ast.Subscript):
            # Resolve the subscripted value.
            return self._self_attribute(node.value)
        # Return no identity for unrelated targets.
        return ""

    # Classify an initializer without evaluating it.
    def _initializer_kind(self, value: ast.AST | None) -> str:
        # Preserve literal mutable containers.
        if isinstance(value, (ast.Dict, ast.List, ast.Set, ast.DictComp, ast.ListComp, ast.SetComp)):
            # Name the static container family.
            return "mutable_container"
        # Preserve direct constructor calls.
        if isinstance(value, ast.Call):
            # Resolve the constructor identity.
            factory = _call_leaf_name(value.func)
            # Name synchronization instances explicitly.
            if factory in LOCK_FACTORY_NAMES:
                # Return the process-local lock family.
                return f"lock:{factory}"
            # Name mutable container factories explicitly.
            if factory in MUTABLE_FACTORY_NAMES:
                # Return the mutable factory identity.
                return f"mutable:{factory}"
            # Name all other constructed objects conservatively.
            return f"object:{factory or 'dynamic'}"
        # Preserve scalar/None seeds because later mutation makes them state.
        if isinstance(value, ast.Constant):
            # Return the exact scalar category without exposing its value.
            return f"scalar:{type(value.value).__name__}"
        # Preserve injected dependencies and computed values.
        return "computed"

    # Record direct self assignments.
    def visit_Assign(self, node: ast.Assign) -> None:
        # Inspect every assignment target.
        for target in node.targets:
            # Resolve one direct self attribute.
            attribute = self._self_attribute(target)
            # Ignore assignments outside class instance state.
            if not self.class_name or not attribute:
                # Continue to the next target.
                continue
            # Build the stable class/attribute key.
            key = (self.class_name, attribute)
            # Retain initializer structure from __init__.
            if self.method_name == "__init__":
                # Record the latest initializer family.
                self.initializers[key] = self._initializer_kind(node.value)
            else:
                # Count reassignment outside initialization.
                self.mutations[key] = self.mutations.get(key, 0) + 1
        # Continue through assigned expressions.
        self.generic_visit(node)

    # Record annotated assignments through the same target semantics.
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        # Resolve one direct self attribute.
        attribute = self._self_attribute(node.target)
        # Process only class instance state.
        if self.class_name and attribute:
            # Build the stable class/attribute key.
            key = (self.class_name, attribute)
            # Retain initializer structure from __init__.
            if self.method_name == "__init__":
                # Record the annotated initializer family.
                self.initializers[key] = self._initializer_kind(node.value)
            else:
                # Count reassignment outside initialization.
                self.mutations[key] = self.mutations.get(key, 0) + 1
        # Continue through annotations and values.
        self.generic_visit(node)

    # Record augmented instance assignments.
    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # Resolve one self-owned attribute.
        attribute = self._self_attribute(node.target)
        # Count runtime mutation inside a class.
        if self.class_name and attribute:
            # Build the stable class/attribute key.
            key = (self.class_name, attribute)
            # Increment the mutation count.
            self.mutations[key] = self.mutations.get(key, 0) + 1
        # Continue through the expression.
        self.generic_visit(node)

    # Record in-place method mutation of self-owned containers.
    def visit_Call(self, node: ast.Call) -> None:
        # Require one recognized mutating attribute method.
        if isinstance(node.func, ast.Attribute) and node.func.attr in MUTATING_METHOD_NAMES:
            # Resolve the self-owned receiver.
            attribute = self._self_attribute(node.func.value)
            # Count the mutation when it belongs to the current class.
            if self.class_name and attribute:
                # Build the stable class/attribute key.
                key = (self.class_name, attribute)
                # Increment the mutation count.
                self.mutations[key] = self.mutations.get(key, 0) + 1
        # Continue through nested calls.
        self.generic_visit(node)


# Read bytes through one patchable boundary and fixed internal failure.
def _read_bytes(path: Path) -> bytes:
    # Attempt one exact binary read.
    try:
        # Return raw bytes so hashing and decoding share one source.
        return path.read_bytes()
    # Normalize every file-system failure without retaining its path.
    except OSError:
        # Raise one value-free internal error.
        raise MultiprocessSafetyAuditError("source inventory unavailable") from None


# Resolve one exact Git command through a fixed privacy boundary.
def _git(repo_root: Path, arguments: list[str]) -> str:
    # Execute only caller-internal fixed Git arguments without a shell.
    try:
        # Capture bounded output for provenance or cleanliness.
        result = subprocess.run(
            ["git", *arguments],  # Use the fixed repository-local Git operation.
            cwd=repo_root,  # Bind the command to the isolated checkout.
            check=True,  # Reject nonzero repository results.
            capture_output=True,  # Keep raw command output out of the CLI.
            text=True,  # Decode Git output as text.
            timeout=10,  # Bound damaged repository or process hangs.
        )
    # Normalize launch, timeout, and command failures.
    except (OSError, subprocess.SubprocessError):
        # Raise one value-free provenance error.
        raise MultiprocessSafetyAuditError("source provenance unavailable") from None
    # Return exact captured standard output to the trusted caller.
    return result.stdout


# Resolve the exact checked-out Git identity.
def source_commit(repo_root: Path) -> str:
    # Normalize the fixed Git output.
    commit = _git(repo_root, ["rev-parse", "HEAD"]).strip().lower()
    # Reject abbreviated, malformed, or multi-line identities.
    if SOURCE_COMMIT_PATTERN.fullmatch(commit) is None:
        # Raise one value-free provenance error.
        raise MultiprocessSafetyAuditError("source provenance unavailable")
    # Return the exact checkout identity.
    return commit


# Require no tracked or untracked checkout changes before evidence creation.
def require_clean_tree(repo_root: Path) -> None:
    # Read the complete tracked and untracked porcelain inventory.
    status = _git(repo_root, ["status", "--porcelain=v1", "--untracked-files=all"])
    # Reject any byte of dirty-tree output without echoing filenames.
    if status.strip():
        # Raise one fixed cleanliness error.
        raise MultiprocessSafetyAuditError("analyzed tree is not clean")


# Load every analyzed production source and governed game manifest.
def _source_records(repo_root: Path) -> tuple[list[dict], list[dict], str]:
    # Collect production Python paths and the audit implementation itself.
    python_paths = sorted((repo_root / "casino").rglob("*.py"), key=lambda item: item.as_posix())
    # Add the tracked audit source so evidence binds its own analysis logic.
    python_paths.append(repo_root / "scripts" / "audit_multiprocess_safety.py")
    # Collect every governed module descriptor.
    manifest_paths = sorted((repo_root / "modules").glob("*.json"), key=lambda item: item.name)
    # Initialize one deterministic relevant-tree digest.
    digest = hashlib.sha256()
    # Collect parsed Python modules with portable identities.
    modules = []
    # Read and parse every production/audit Python source.
    for path in python_paths:
        # Derive the portable repository path.
        relative_path = path.relative_to(repo_root).as_posix()
        # Read exact bytes once for digest and parsing.
        raw = _read_bytes(path)
        # Add a length-framed relative path and exact bytes to the digest.
        digest.update(relative_path.encode("utf-8") + b"\0" + str(len(raw)).encode("ascii") + b"\0" + raw)
        # Parse strict UTF-8 source through the fixed error boundary.
        try:
            # Retain one source record for structural passes.
            modules.append({"path": relative_path, "tree": ast.parse(raw.decode("utf-8"), filename=relative_path)})
        # Normalize malformed source without leaking content or path.
        except (UnicodeError, SyntaxError):
            # Raise one fixed inventory error.
            raise MultiprocessSafetyAuditError("source inventory unavailable") from None
    # Collect decoded manifest records.
    manifests = []
    # Read every governed descriptor.
    for path in manifest_paths:
        # Derive the portable repository path.
        relative_path = path.relative_to(repo_root).as_posix()
        # Read exact manifest bytes.
        raw = _read_bytes(path)
        # Bind descriptor identity and bytes to the same relevant-tree digest.
        digest.update(relative_path.encode("utf-8") + b"\0" + str(len(raw)).encode("ascii") + b"\0" + raw)
        # Decode and parse the governed descriptor.
        try:
            # Retain one exact manifest record.
            manifests.append({"path": relative_path, "data": json.loads(raw.decode("utf-8"))})
        # Normalize malformed bytes or JSON without retaining source content.
        except (UnicodeError, json.JSONDecodeError):
            # Raise one fixed inventory error.
            raise MultiprocessSafetyAuditError("manifest inventory unavailable") from None
    # Return parsed sources, descriptors, and exact relevant-tree digest.
    return modules, manifests, digest.hexdigest()


# Collect calls reachable from exact live entrypoints and module initializers.
def _reachable_facts(
    modules: list[dict],  # Limit analysis to one reviewed source boundary.
    root_names: set[str],  # Seed the graph from exact live entrypoints.
    *,  # Require explicit initializer ownership.
    include_module_initializers: bool = False,  # Include import-time construction only when reviewed.
) -> dict:  # Return sanitized structural facts.
    # Index top-level function and class definitions by static name across the bounded source set.
    definitions: dict[str, list[ast.AST]] = {}
    # Inspect every parsed module.
    for module in modules:
        # Inspect module declarations only.
        for statement in module["tree"].body:
            # Index top-level functions, asynchronous functions, and classes.
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Retain every same-named definition conservatively.
                definitions.setdefault(statement.name, []).append(statement)
    # Require every declared root to resolve inside the bounded source set.
    if not root_names <= set(definitions):
        # Reject stale or incomplete entrypoint ownership.
        raise MultiprocessSafetyAuditError("reachable source inventory unavailable")
    # Seed the traversal queue from exact entrypoints.
    queue = [definition for name in sorted(root_names) for definition in definitions[name]]
    # Retain visited definition identities to avoid recursion loops.
    visited: set[int] = set()
    # Collect reachable call records.
    calls: list[dict] = []
    # Collect reachable static references.
    names: set[str] = set()
    # Optionally treat constructed module objects as live initialization roots.
    if include_module_initializers:
        # Inspect every module initializer without entering declarations.
        for module in modules:
            # Create one module-body collector.
            collector = ReachableBodyCollector()
            # Visit only non-definition module statements.
            for statement in module["tree"].body:
                # Skip declarations until called from a live root.
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # Continue to the next module statement.
                    continue
                # Visit executable module initialization.
                collector.visit(statement)
            # Retain initializer calls and references.
            calls.extend(collector.calls)
            # Merge initializer references into the call graph.
            names.update(collector.names)
        # Queue every definition referenced during module initialization.
        queue.extend(definition for name in sorted(names) for definition in definitions.get(name, []))
    # Traverse reachable functions, classes, and registered nested callbacks.
    while queue:
        # Remove the next bounded definition.
        definition = queue.pop(0)
        # Skip a definition already traversed through recursion or aliases.
        if id(definition) in visited:
            # Continue to the next queued definition.
            continue
        # Mark this exact AST definition visited.
        visited.add(id(definition))
        # Collect class methods when the class constructor is reachable.
        if isinstance(definition, ast.ClassDef):
            # Queue every direct method because a live instance may dispatch it through an attribute.
            queue.extend(
                statement  # Queue one potentially dispatched method.
                for statement in definition.body  # Inspect direct methods only.
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))  # Exclude constants and nested classes.
            )
            # Continue without traversing unrelated class constants.
            continue
        # Create one body collector for the reachable function.
        collector = ReachableBodyCollector()
        # Visit default expressions because injected production boundaries execute at definition time.
        for default in [*definition.args.defaults, *definition.args.kw_defaults]:
            # Skip absent keyword-only defaults.
            if default is not None:
                # Visit the reachable default expression.
                collector.visit(default)
        # Visit each executable function statement.
        for statement in definition.body:
            # Traverse the reachable body while excluding unregistered nested helpers.
            collector.visit(statement)
        # Retain reachable calls and static references.
        calls.extend(collector.calls)
        # Merge reachable names for injected boundary proof.
        names.update(collector.names)
        # Queue registered nested callbacks.
        queue.extend(collector.callbacks)
        # Queue every referenced local function or class definition.
        queue.extend(
            local_definition  # Queue one statically referenced declaration.
            for name in sorted(collector.names)  # Traverse references deterministically.
            for local_definition in definitions.get(name, [])  # Ignore unresolved external names.
        )
    # Return complete bounded reachability evidence.
    return {"calls": calls, "names": names, "definition_count": len(visited)}


# Count atomic updates, direct reads, and direct writes against one document symbol.
def _document_call_counts(calls: list[dict], document_symbol: str) -> dict[str, int]:
    # Retain only calls whose first argument is the exact document symbol.
    owned_calls = [
        call  # Retain one executable call.
        for call in calls  # Inspect only reachable call records.
        if isinstance(call["first_argument"], ast.Name)  # Require a static document symbol.
        and call["first_argument"].id == document_symbol  # Require exact document ownership.
    ]
    # Return exact semantic call counts without source substrings.
    return {
        "atomic": sum(call["name"] in {"update_json", "update_json_strict"} for call in owned_calls),  # Count updates.
        "read": sum(call["name"] == "read_json" for call in owned_calls),  # Count direct reads.
        "write": sum(call["name"] == "write_json" for call in owned_calls),  # Count direct writes.
    }


# Classify document mutation semantics and fail closed on mixed or missing atomic paths.
def _document_semantics(counts: dict[str, int]) -> tuple[str, str]:
    # Require one reachable provider-atomic mutation before compatibility is possible.
    if counts["atomic"] <= 0:
        # Reject marker-only or absent transaction paths.
        raise MultiprocessSafetyAuditError("component inventory unavailable")
    # Block any reachable direct whole-document write alongside atomic paths.
    if counts["write"] > 0:
        # Return explicit mixed-path semantics.
        return "mixed_atomic_and_direct_document_writes", "blocked"
    # Preserve provider-atomic semantics only when no parallel direct path exists.
    return "provider_atomic_document", "compatible"


# Discover every public top-level entrypoint that can reach one owned state boundary.
def _public_state_entrypoints(
    modules: list[dict],  # Limit discovery to one reviewed component.
    *,  # Require explicit state-call ownership arguments.
    read_calls: set[str],  # Name calls that only read owned state.
    mutation_calls: set[str],  # Name calls that mutate owned state.
    document_symbol: str = "",  # Optionally require an exact first-argument document symbol.
) -> dict:  # Return exact public mutating and read-only roots.
    # Collect every public top-level function and asynchronous function name.
    public_names = {
        statement.name  # Preserve one externally callable static name.
        for module in modules  # Inspect every bounded component source.
        for statement in module["tree"].body  # Inspect module declarations only.
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))  # Select functions.
        and not statement.name.startswith("_")  # Exclude private implementation helpers as roots.
    }
    # Collect public entrypoints that can mutate the owned state.
    mutating = set()
    # Collect public entrypoints whose owned-state reachability is read-only.
    read_only = set()
    # Analyze every public function independently so omissions cannot hide behind another root.
    for name in sorted(public_names):
        # Resolve the complete bounded call graph from this candidate.
        reachability = _reachable_facts(modules, {name})
        # Select calls that address the exact owned document when one is declared.
        owned_calls = [
            call  # Retain one reachable state call.
            for call in reachability["calls"]  # Inspect every reachable call.
            if not document_symbol  # Accept named-call ownership when no document symbol applies.
            or (  # Otherwise require the exact owned document symbol.
                isinstance(call["first_argument"], ast.Name)  # Require a static first argument.
                and call["first_argument"].id == document_symbol  # Require exact document ownership.
            )
        ]
        # Count reachable mutations before classifying read-only entrypoints.
        mutation_count = sum(call["name"] in mutation_calls for call in owned_calls)
        # Count reachable state reads independently.
        read_count = sum(call["name"] in read_calls for call in owned_calls)
        # Classify every public path that can reach a mutation as a mutator.
        if mutation_count > 0:
            # Retain the exact mutating entrypoint.
            mutating.add(name)
        elif read_count > 0:  # Classify a state reader only when no mutation is reachable.
            # Retain an exact read-only state entrypoint.
            read_only.add(name)
    # Return deterministic derived ownership for reconciliation and evidence.
    return {"mutating": sorted(mutating), "read_only": sorted(read_only)}


# Require declared mutating and read-only roots to equal structural public-entrypoint discovery.
def _reconcile_state_entrypoints(
    discovered: dict,  # Supply structurally derived public ownership.
    declared_mutators: set[str],  # Supply reviewed mutating roots.
    declared_read_only: set[str],  # Supply reviewed read-only roots.
) -> dict:  # Return deterministic reconciled ownership.
    # Require disjoint declared dispositions.
    if declared_mutators & declared_read_only:
        # Reject ambiguous public ownership.
        raise MultiprocessSafetyAuditError("entrypoint inventory unavailable")
    # Normalize structural discovery to exact sets.
    discovered_mutators = set(discovered["mutating"])
    # Normalize structurally discovered read-only entrypoints.
    discovered_read_only = set(discovered["read_only"])
    # Require exact equality so every new public mutator fails closed until reviewed.
    if discovered_mutators != declared_mutators:
        # Reject omitted, stale, or incorrectly read-only mutating roots.
        raise MultiprocessSafetyAuditError("entrypoint inventory unavailable")
    # Require exact equality for public read-only state paths as well.
    if discovered_read_only != declared_read_only:
        # Reject omitted, stale, or incorrectly mutating read-only roots.
        raise MultiprocessSafetyAuditError("entrypoint inventory unavailable")
    # Return deterministic reconciled evidence.
    return {
        "mutating": sorted(discovered_mutators),  # Publish complete mutator ownership.
        "read_only": sorted(discovered_read_only),  # Publish complete read-only ownership.
    }


# Return static string keys from one named module dictionary.
def _module_dict_keys(tree: ast.Module, symbol: str) -> set[str]:
    # Inspect module declarations only.
    for statement in tree.body:
        # Normalize ordinary assignment targets.
        if isinstance(statement, ast.Assign):
            # Read every direct target name.
            targets = [target.id for target in statement.targets if isinstance(target, ast.Name)]
            # Retain the assigned value.
            value = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):  # Normalize annotations.
            # Normalize one annotated direct target.
            targets = [statement.target.id]
            # Retain the assigned value.
            value = statement.value
        else:
            # Ignore unrelated module statements.
            continue
        # Select only the exact requested dictionary.
        if symbol not in targets or not isinstance(value, ast.Dict):
            # Continue to the next declaration.
            continue
        # Collect exact static string keys.
        keys = {
            key.value  # Preserve one static string key.
            for key in value.keys  # Inspect every mapping key.
            if isinstance(key, ast.Constant) and isinstance(key.value, str)  # Reject dynamic keys.
        }
        # Require every dictionary key to be a static string.
        if len(keys) != len(value.keys):
            # Reject a dynamic ownership declaration.
            raise MultiprocessSafetyAuditError("component inventory unavailable")
        # Return the exact key set.
        return keys
    # Reject a missing ownership declaration.
    raise MultiprocessSafetyAuditError("component inventory unavailable")


# Load every catalog game and validate its backend ownership.
def _registered_games(manifests: list[dict], module_paths: set[str]) -> list[dict]:
    # Collect governed game records only.
    games = []
    # Inspect every parsed module descriptor.
    for manifest in manifests:
        # Read the optional game catalog object.
        game = manifest["data"].get("game") if isinstance(manifest["data"], dict) else None
        # Skip non-game modules.
        if not isinstance(game, dict):
            # Continue to the next descriptor.
            continue
        # Read the stable game identity without coercion.
        game_id = game.get("id")
        # Require one conservative portable game identifier.
        if not isinstance(game_id, str) or re.fullmatch(r"[a-z0-9_]+", game_id) is None:
            # Reject malformed catalog ownership.
            raise MultiprocessSafetyAuditError("game catalog unavailable")
        # Read the exact backend registration identity.
        backend = game.get("backend")
        # Require one static backend mapping.
        if not isinstance(backend, dict) or not isinstance(backend.get("register"), str):
            # Reject incomplete backend ownership.
            raise MultiprocessSafetyAuditError("game catalog unavailable")
        # Split the fixed callback identity.
        module_name, separator, callback = backend["register"].partition(":")
        # Require the callback to stay within its isolated game package.
        if separator != ":" or callback != "register" or not module_name.startswith(f"casino.games.{game_id}."):
            # Reject dynamic or cross-game routing.
            raise MultiprocessSafetyAuditError("game catalog unavailable")
        # Convert the module identity to its portable source path.
        backend_path = module_name.replace(".", "/") + ".py"
        # Require the registered source to be part of the analyzed tree.
        if backend_path not in module_paths:
            # Reject stale catalog callbacks.
            raise MultiprocessSafetyAuditError("game catalog unavailable")
        # Retain only sanitized governed facts.
        games.append({"game_id": game_id, "backend": module_name})
    # Require exact deployed catalog cardinality.
    if len(games) != EXPECTED_GAME_COUNT:
        # Fail closed on additions or omissions.
        raise MultiprocessSafetyAuditError("game catalog unavailable")
    # Reject duplicate game identities.
    if len({row["game_id"] for row in games}) != len(games):
        # Fail closed on ambiguous ownership.
        raise MultiprocessSafetyAuditError("game catalog unavailable")
    # Return deterministic catalog order.
    return sorted(games, key=lambda row: row["game_id"])


# Discover and classify module-level locks, mutable globals, caches, and singletons.
def _module_state_inventory(modules: list[dict], game_ids: set[str]) -> list[dict]:
    # Collect one normalized state row per relevant module assignment.
    rows = []
    # Inspect every parsed module.
    for module in modules:
        # Ignore the audit implementation itself as runtime state.
        if not module["path"].startswith("casino/"):
            # Continue to the next source.
            continue
        # Collect runtime mutation sites for declared symbols.
        mutations = ModuleMutationCollector()
        # Traverse executable syntax.
        mutations.visit(module["tree"])
        # Collect every direct and conditional module initializer without entering declarations.
        assignment_collector = ModuleAssignmentCollector()
        # Traverse executable module initialization.
        assignment_collector.visit(module["tree"])
        # Classify every direct target independently.
        for symbol, value in assignment_collector.assignments:
            # Resolve assigned structure without evaluating it.
            factory = _call_leaf_name(value.func) if isinstance(value, ast.Call) else ""
            # Detect a process-local synchronization primitive.
            is_lock = factory in LOCK_FACTORY_NAMES
            # Detect mutable literal/container declarations.
            is_container = isinstance(value, (ast.Dict, ast.List, ast.Set, ast.DictComp, ast.ListComp, ast.SetComp))
            # Detect explicit mutable container constructors.
            is_container_factory = factory in MUTABLE_FACTORY_NAMES
            # Detect lazy private singleton/cache declarations.
            is_lazy_private = isinstance(value, ast.Constant) and value.value is None and symbol.startswith("_")
            # Detect every constructed module object regardless of symbol naming.
            is_constructed = isinstance(value, ast.Call)
            # Read the exact number of detected runtime mutations before filtering initializer types.
            mutation_count = mutations.counts.get(symbol, 0)
            # Ignore only declarations with no mutable structure and no runtime mutation.
            if not (
                is_lock  # Retain synchronization primitives.
                or is_container  # Retain literal mutable containers.
                or is_container_factory  # Retain constructed mutable containers.
                or is_lazy_private  # Retain lazy private caches.
                or is_constructed  # Retain every constructed object.
                or mutation_count  # Retain every runtime-mutated declaration.
            ):  # Drop only immutable and unmutated declarations.
                # Continue to the next target.
                continue
            # Split portable path ownership.
            parts = module["path"].split("/")
            # Resolve an owning registered game when present.
            game_id = parts[2] if len(parts) >= 4 and parts[:2] == ["casino", "games"] and parts[2] in game_ids else ""
            # Classify known synchronization primitives first.
            if is_lock:
                # Bind every game lock to its game blocker.
                if game_id:
                    # Record the process-local game action boundary.
                    state_model, status = "game_process_local_lock", "blocked"
                elif module["path"] in KNOWN_CORE_LOCKS:  # Match one reviewed core lock.
                    # Use the reviewed core lock semantics.
                    state_model, status = KNOWN_CORE_LOCKS[module["path"]]
                else:
                    # Conservatively block any newly discovered core lock.
                    state_model, status = "unclassified_process_local_lock", "blocked"
                # Name the synchronization factory.
                kind = f"lock:{factory}"
            elif (module["path"], symbol) in KNOWN_CORE_SINGLETONS:  # Match one reviewed singleton.
                # Reuse reviewed semantics for exact core singleton/cache symbols.
                state_model, status = KNOWN_CORE_SINGLETONS[(module["path"], symbol)]
                # Name the assignment as a singleton/cache.
                kind = f"singleton:{factory or 'lazy'}"
            elif factory in COMPATIBLE_SINGLETON_FACTORIES:  # Match one reviewed independent factory.
                # Preserve independent entropy sources as intentional per-process objects.
                state_model, status = "per_process_entropy_source", "compatible"
                # Name the exact entropy singleton factory.
                kind = f"singleton:{factory}"
            elif is_container or is_container_factory:  # Classify literal and constructed containers.
                # Block every mutable container unless source wraps it in a reviewed immutable factory.
                state_model, status = "mutable_module_container", "blocked"
                # Name the structural container family.
                kind = f"container:{factory or type(value).__name__}"
            elif mutation_count:  # Classify every remaining runtime-mutated declaration.
                # Block every reassigned scalar or object not covered by an exact reviewed singleton.
                state_model, status = "mutated_module_scalar_or_object", "blocked"
                # Name the initializer shape without publishing its value.
                kind = f"mutated:{factory or type(value).__name__}"
            elif factory in IMMUTABLE_MODULE_FACTORIES:  # Classify reviewed immutable constructions.
                # Preserve known scalar/immutable construction as compatible module state.
                state_model, status = "immutable_or_scalar_module_value", "compatible"
                # Name the exact static factory.
                kind = f"value:{factory}"
            elif game_id:  # Bind unknown game objects to their game blocker.
                # Block every module-owned constructed game object conservatively.
                state_model, status = "game_service_singleton", "blocked"
                # Name the exact service constructor.
                kind = f"singleton:{factory or 'dynamic'}"
            else:
                # Conservatively block every other constructed or lazy singleton.
                state_model, status = "process_local_singleton_or_cache", "blocked"
                # Name the static singleton constructor or lazy seed.
                kind = f"singleton:{factory or 'lazy'}"
            # Append only sanitized structural fields.
            rows.append(
                {
                    "path": module["path"],  # Preserve repository-relative source identity.
                    "symbol": symbol,  # Preserve the static module symbol.
                    "kind": kind,  # Publish its structural family.
                    "mutation_sites": mutation_count,  # Publish the bounded mutation count.
                    "state_model": state_model,  # Publish its reviewed/conservative semantics.
                    "multiworker_status": status,  # Publish its explicit worker disposition.
                }
            )
    # Return deterministic source/symbol order.
    return sorted(rows, key=lambda row: (row["path"], row["symbol"], row["kind"]))


# Discover and conservatively classify mutable instance-held state and locks.
def _instance_state_inventory(modules: list[dict]) -> list[dict]:
    # Collect normalized instance-state rows.
    rows = []
    # Inspect every production module.
    for module in modules:
        # Ignore the audit implementation itself.
        if not module["path"].startswith("casino/"):
            # Continue to the next source.
            continue
        # Collect class initializer and mutation facts.
        collector = InstanceStateCollector()
        # Traverse executable class syntax.
        collector.visit(module["tree"])
        # Consider every initialized or subsequently mutated instance attribute.
        keys = sorted(set(collector.initializers) | set(collector.mutations))
        # Classify each class-owned state surface.
        for class_name, attribute in keys:
            # Resolve initializer family or a mutation-only marker.
            initializer = collector.initializers.get((class_name, attribute), "mutation_only")
            # Resolve the bounded runtime mutation count.
            mutation_count = collector.mutations.get((class_name, attribute), 0)
            # Detect a lock or mutable initialization even when no later assignment exists.
            intrinsically_mutable = initializer.startswith(("lock:", "mutable:")) or initializer == "mutable_container"
            # Ignore injected dependencies and immutable attributes that never change.
            if not intrinsically_mutable and mutation_count == 0:
                # Continue to the next instance attribute.
                continue
            # Preserve explicit process-local MySQL pool/lease state as compatible per worker.
            if module["path"] == "casino/core/mysql_pool.py":  # Bind explicit per-process pool state.
                # Record the process-bound pool lifecycle model.
                state_model, status = "process_bound_mysql_pool_state", "compatible"
            elif module["path"] == "casino/operations/service.py":  # Bind Operations state.
                # Block the process-local Operations heartbeat.
                state_model, status = "process_local_operations_state", "blocked"
            elif module["path"] == "casino/core/security.py" and class_name == "RateLimiter":  # Bind limiter state.
                # Block the per-worker general request allowance registry.
                state_model, status = "process_local_rate_limit_state", "blocked"
            elif module["path"] == "casino/core/storage.py":  # Bind provider caches and locks.
                # Conservatively block provider caches until each cross-process refresh path is proven.
                state_model, status = "provider_instance_cache_or_lock", "blocked"
            elif module["path"].startswith("casino/games/"):  # Bind mutable game instance state.
                # Conservatively bind game instance state to the game settlement blocker.
                state_model, status = "game_instance_mutable_state", "blocked"
            else:
                # Conservatively block every remaining mutable instance surface.
                state_model, status = "unclassified_instance_mutable_state", "blocked"
            # Append only sanitized structural fields.
            rows.append(
                {
                    "path": module["path"],  # Preserve repository-relative source identity.
                    "class": class_name,  # Preserve the static class identity.
                    "attribute": attribute,  # Preserve the static instance attribute.
                    "initializer": initializer,  # Publish only initializer structure.
                    "mutation_sites": mutation_count,  # Publish the bounded mutation count.
                    "state_model": state_model,  # Publish conservative process semantics.
                    "multiworker_status": status,  # Publish the worker disposition.
                }
            )
    # Return deterministic source/class/attribute order.
    return sorted(rows, key=lambda row: (row["path"], row["class"], row["attribute"]))


# Classify exact semantic call-site evidence for required control-plane surfaces.
def _component_inventory(modules: list[dict], module_state: list[dict], instance_state: list[dict]) -> list[dict]:
    # Index parsed modules by portable source path.
    by_path = {module["path"]: module for module in modules}
    # Bind auth analysis to its exact owning source.
    auth_modules = [by_path["casino/core/auth.py"]]
    # Derive every public session state entrypoint independently.
    auth_discovered = _public_state_entrypoints(
        auth_modules,  # Restrict discovery to auth ownership.
        read_calls={"read_json", "read_json_strict"},  # Classify ordinary and strict session reads.
        mutation_calls={"update_json", "update_json_strict", "write_json"},  # Classify all mutations.
        document_symbol="SESSIONS_PATH",  # Require exact session document ownership.
    )
    # Reconcile derived auth ownership against reviewed mutating and read-only dispositions.
    auth_entrypoints = _reconcile_state_entrypoints(
        auth_discovered,  # Supply structural auth discovery.
        AUTH_SESSION_ROOTS,  # Supply reviewed mutating roots.
        AUTH_SESSION_READ_ONLY_ROOTS,  # Supply reviewed read-only roots.
    )
    # Resolve calls reachable from exact live session entrypoints.
    session_reachability = _reachable_facts(
        auth_modules,  # Restrict analysis to the auth owner.
        AUTH_SESSION_ROOTS,  # Seed every live session entrypoint.
    )
    # Count reachable session document semantics.
    session_calls = _document_call_counts(session_reachability["calls"], "SESSIONS_PATH")
    # Read the exact provider-atomic call count.
    atomic_session_calls = session_calls["atomic"]
    # Read the exact direct whole-document write count.
    direct_session_writes = session_calls["write"]
    # Classify session paths from bounded reachable calls.
    session_model, session_status = _document_semantics(session_calls)
    # Select structural rate-limiter instance state.
    limiter_rows = [
        row  # Retain one limiter instance-state row.
        for row in instance_state  # Inspect complete instance inventory.
        if row["path"] == "casino/core/security.py" and row["class"] == "RateLimiter"  # Match exact owner.
    ]
    # Require both the client registry and lock.
    if {row["attribute"] for row in limiter_rows} < {"clients", "lock"}:
        # Reject incomplete security classification.
        raise MultiprocessSafetyAuditError("component inventory unavailable")
    # Select structural Operations heartbeat state.
    heartbeat_rows = [
        row  # Retain one heartbeat instance-state row.
        for row in instance_state  # Inspect complete instance inventory.
        if row["path"] == "casino/operations/service.py" and row["class"] == "OperationsProbeService"  # Match owner.
    ]
    # Require both heartbeat value and synchronization boundary.
    if {row["attribute"] for row in heartbeat_rows} < {"_heartbeat_lock", "_last_successful_heartbeat_at"}:
        # Reject incomplete Operations classification.
        raise MultiprocessSafetyAuditError("component inventory unavailable")
    # Select the structural autoplay lock.
    autoplay_locks = [
        row  # Retain the one autoplay lock.
        for row in module_state  # Inspect complete module inventory.
        if row["path"] == "casino/core/autoplay.py" and row["symbol"] == "AUTOPLAY_REGISTRY_LOCK"  # Match owner.
    ]
    # Bind autoplay analysis to its exact owning source.
    autoplay_modules = [by_path["casino/core/autoplay.py"]]
    # Derive every public autoplay state entrypoint independently.
    autoplay_discovered = _public_state_entrypoints(
        autoplay_modules,  # Restrict discovery to autoplay ownership.
        read_calls={"read_json"},  # Classify registry document reads.
        mutation_calls={"update_json", "update_json_strict", "write_json"},  # Classify registry mutations.
        document_symbol="AUTOPLAY_PATH",  # Require exact autoplay document ownership.
    )
    # Reconcile derived autoplay ownership against reviewed dispositions.
    autoplay_entrypoints = _reconcile_state_entrypoints(
        autoplay_discovered,  # Supply structural autoplay discovery.
        AUTOPLAY_ROOTS,  # Supply reviewed mutating roots.
        AUTOPLAY_READ_ONLY_ROOTS,  # Supply reviewed read-only roots.
    )
    # Resolve calls reachable from every public autoplay lifecycle entrypoint.
    autoplay_reachability = _reachable_facts(
        autoplay_modules,  # Restrict analysis to autoplay ownership.
        AUTOPLAY_ROOTS,  # Seed every lifecycle entrypoint.
    )
    # Count reachable autoplay document semantics.
    autoplay_calls = _document_call_counts(autoplay_reachability["calls"], "AUTOPLAY_PATH")
    # Read the exact autoplay document-read count.
    autoplay_reads = autoplay_calls["read"]
    # Read the exact autoplay document-write count.
    autoplay_writes = autoplay_calls["write"]
    # Require a concrete local lock plus complete document reads and writes.
    if len(autoplay_locks) != 1 or autoplay_reads == 0 or autoplay_writes == 0:
        # Reject incomplete autoplay semantics.
        raise MultiprocessSafetyAuditError("component inventory unavailable")
    # Read the exact declared bot ownership from profiles.
    bot_games = _module_dict_keys(by_path["casino/bots/profiles.py"]["tree"], "DEFAULT_STAKES")
    # Bind bot analysis to its exact controller source.
    bot_modules = [by_path["casino/bots/controller.py"]]
    # Derive every public bot state entrypoint independently.
    bot_discovered = _public_state_entrypoints(
        bot_modules,  # Restrict discovery to bot controller ownership.
        read_calls={"load_game_state"},  # Classify game-state reads.
        mutation_calls={"save_game_state"},  # Classify game-state writes.
    )
    # Reconcile derived bot ownership against reviewed dispositions.
    bot_entrypoints = _reconcile_state_entrypoints(
        bot_discovered,  # Supply structural bot discovery.
        BOT_ROOTS,  # Supply every reviewed mutating dispatcher.
        BOT_READ_ONLY_ROOTS,  # Supply the reviewed empty read-only set.
    )
    # Resolve calls reachable from the public bot dispatcher.
    bot_reachability = _reachable_facts(
        bot_modules,  # Restrict analysis to the bot controller.
        BOT_ROOTS,  # Seed the public dispatcher.
    )
    # Read exact reachable bot controller call sites.
    bot_calls = bot_reachability["calls"]
    # Resolve statically owned game ids from load calls.
    bot_loads = {
        call["first_argument"].value  # Preserve one static game identity.
        for call in bot_calls  # Inspect reachable bot calls.
        if call["name"] == "load_game_state"  # Select game-state loads.
        and isinstance(call["first_argument"], ast.Constant)  # Require a static literal.
        and isinstance(call["first_argument"].value, str)  # Require a string game id.
    }
    # Resolve statically owned game ids from save calls.
    bot_saves = {
        call["first_argument"].value  # Preserve one static game identity.
        for call in bot_calls  # Inspect reachable bot calls.
        if call["name"] == "save_game_state"  # Select game-state saves.
        and isinstance(call["first_argument"], ast.Constant)  # Require a static literal.
        and isinstance(call["first_argument"].value, str)  # Require a string game id.
    }
    # Require exact profile/load/save ownership equality.
    if not bot_games or bot_games != bot_loads or bot_games != bot_saves:
        # Reject partial or dynamic bot ownership proof.
        raise MultiprocessSafetyAuditError("component inventory unavailable")
    # Return exact semantic component dispositions.
    return [
        {
            "component": "auth_sessions",  # Name the session persistence surface.
            "state_model": session_model,  # Expose compatible or mixed path semantics.
            "multiworker_status": session_status,  # Fail closed on any reachable direct path.
            "atomic_call_sites": atomic_session_calls,  # Publish executable atomic call count.
            "direct_write_call_sites": direct_session_writes,  # Publish executable unsafe call count.
            "reachable_definitions": session_reachability["definition_count"],  # Reconcile bounded call-graph scope.
            "mutating_entrypoints": auth_entrypoints["mutating"],  # Publish complete auth mutation ownership.
            "read_only_entrypoints": auth_entrypoints["read_only"],  # Publish complete auth read ownership.
        },
        {
            "component": "request_rate_limiter",  # Name the general security limiter.
            "state_model": "process_local_mutable_registry",  # Expose divergent worker state.
            "multiworker_status": "blocked",  # Refuse a second worker.
            "instance_state_count": len(limiter_rows),  # Reconcile structural class state.
        },
        {
            "component": "operations_heartbeat",  # Name the Operations heartbeat.
            "state_model": "process_local_heartbeat",  # Expose worker-local monotonic state.
            "multiworker_status": "blocked",  # Refuse shared-heartbeat claims.
            "instance_state_count": len(heartbeat_rows),  # Reconcile structural class state.
        },
        {
            "component": "autoplay_registry",  # Name the autoplay control plane.
            "state_model": "process_local_locked_whole_document_rmw",  # Expose the split transaction.
            "multiworker_status": "blocked",  # Refuse a second worker.
            "read_call_sites": autoplay_reads,  # Publish exact executable reads.
            "write_call_sites": autoplay_writes,  # Publish exact executable writes.
            "reachable_definitions": autoplay_reachability["definition_count"],  # Reconcile lifecycle call graph.
            "mutating_entrypoints": autoplay_entrypoints["mutating"],  # Publish complete lifecycle ownership.
            "read_only_entrypoints": autoplay_entrypoints["read_only"],  # Publish complete read ownership.
        },
        {
            "component": "bot_controller",  # Name bot-owned game mutation.
            "state_model": "shared_game_whole_document_rmw",  # Expose stale-write risk.
            "multiworker_status": "blocked",  # Refuse a second worker.
            "owned_games": sorted(bot_games),  # Publish every declared bot game.
            "reachable_definitions": bot_reachability["definition_count"],  # Reconcile dispatcher call graph.
            "mutating_entrypoints": bot_entrypoints["mutating"],  # Publish complete bot mutation ownership.
            "read_only_entrypoints": bot_entrypoints["read_only"],  # Publish complete bot read ownership.
        },
    ]


# Classify every registered game from executable AST calls and imports.
def _game_inventory(games: list[dict], modules: list[dict]) -> list[dict]:
    # Select the one shared settlement helper whose production defaults own delegated state publication.
    simple_game_modules = [module for module in modules if module["path"] == "casino/core/simple_game.py"]
    # Start with no accepted delegated atomic call when a focused fixture omits the shared helper.
    simple_game_atomic_updates = 0
    # Start with no reachable direct helper save in focused fixtures or current production.
    simple_game_direct_saves = 0
    # Analyze the helper exactly once when the complete repository source is present.
    if simple_game_modules:
        # Require one unambiguous helper source owner.
        if len(simple_game_modules) != 1:
            # Reject duplicate or ambiguous shared settlement implementations.
            raise MultiprocessSafetyAuditError("game inventory unavailable")
        # Traverse every method because a constructed helper may dispatch any public or private method.
        simple_game_reachability = _reachable_facts(simple_game_modules, {"SimpleWagerGame"})
        # Count the provider-current production updater wired by the helper.
        simple_game_atomic_updates = sum(call["name"] == "update_player_game_state" for call in simple_game_reachability["calls"])
        # Count any reachable detached whole-document save that would invalidate delegated atomicity.
        simple_game_direct_saves = sum(call["name"] == "save_player_game_state" for call in simple_game_reachability["calls"])
    # Collect exact per-game dispositions.
    rows = []
    # Inspect each registered game package.
    for game in games:
        # Select only parsed sources owned by this package.
        package_prefix = f"casino/games/{game['game_id']}/"
        # Retain package sources in deterministic order.
        package_modules = [module for module in modules if module["path"].startswith(package_prefix)]
        # Require at least the registered backend source.
        if not package_modules:
            # Reject missing package ownership.
            raise MultiprocessSafetyAuditError("game inventory unavailable")
        # Resolve calls and references reachable from registration and module singleton initialization.
        reachability = _reachable_facts(
            package_modules,  # Restrict analysis to one registered game package.
            {"register"},  # Seed the governed registration entrypoint.
            include_module_initializers=True,  # Include constructed services and injected defaults.
        )
        # Read exact reachable calls.
        calls = reachability["calls"]
        # Read exact reachable static names, including injected production defaults.
        reachable_names = reachability["names"]
        # Detect player-document load calls or injected production defaults.
        player_loads = sum(call["name"] == "load_player_game_state" for call in calls) + int(
            "load_player_game_state" in reachable_names  # Preserve injected production defaults.
        )
        # Count executable player-document saves or injected production defaults.
        player_saves = sum(call["name"] == "save_player_game_state" for call in calls) + int(
            "save_player_game_state" in reachable_names  # Preserve injected production defaults.
        )
        # Detect provider-atomic player-document mutations if added.
        atomic_updates = sum(call["name"] == "update_player_game_state" for call in calls)
        # Detect the shared SimpleWagerGame construction/import path.
        simple_game_calls = sum(call["name"] == "SimpleWagerGame" for call in calls)
        # Preserve import evidence because construction may sit behind a factory.
        simple_game_imported = "SimpleWagerGame" in reachable_names
        # Detect player-document ownership through reads, direct saves, or provider-atomic updates.
        uses_player_documents = player_loads > 0 or player_saves > 0 or atomic_updates > 0
        # Detect the current shared simple-game family.
        uses_simple_game = simple_game_calls > 0 or simple_game_imported
        # Require the shared family to resolve through one atomic updater and zero direct saves.
        if uses_simple_game and (simple_game_atomic_updates != 1 or simple_game_direct_saves != 0):
            # Fail closed if a helper regression would make all delegated game classifications stale.
            raise MultiprocessSafetyAuditError("game inventory unavailable")
        # Reject player-document paths that cannot read current state or publish any mutation.
        if uses_player_documents and (player_loads == 0 or (player_saves == 0 and atomic_updates == 0)):
            # Fail closed on incomplete direct or provider-atomic persistence semantics.
            raise MultiprocessSafetyAuditError("game inventory unavailable")
        # Reject a package with neither a direct provider path nor shared-helper delegation.
        if not uses_player_documents and not uses_simple_game:
            # Fail closed when no reachable persistence family exists.
            raise MultiprocessSafetyAuditError("game inventory unavailable")
        # Permit a shared-helper compatibility adapter only when its game-local writes are provider-atomic.
        if uses_simple_game and uses_player_documents and (player_saves != 0 or atomic_updates == 0):
            # Reject any adapted helper path that can still replace a detached whole document.
            raise MultiprocessSafetyAuditError("game inventory unavailable")
        # Name direct or delegated provider-atomic persistence precisely.
        state_model = "player_document_load_save" if uses_player_documents else "provider_atomic_player_document"
        # Expose a fully provider-atomic player-document path after every direct save is retired.
        if uses_player_documents and atomic_updates and player_saves == 0:
            # Distinguish state serialization from broader state-plus-money worker safety.
            state_model = "provider_atomic_player_document"
        # Expose mixed provider-atomic and direct paths without treating them as compatible.
        elif atomic_updates and uses_player_documents:
            # Name the mixed path explicitly.
            state_model = "mixed_atomic_and_direct_player_document_paths"
        # Return one conservative game blocker.
        rows.append(
            {
                "game_id": game["game_id"],  # Preserve catalog identity.
                "backend": game["backend"],  # Preserve registered backend source.
                "state_model": state_model,  # Publish executable persistence semantics.
                "load_call_sites": player_loads,  # Publish direct load count.
                "save_call_sites": player_saves,  # Publish direct save count.
                "atomic_update_call_sites": atomic_updates + (simple_game_atomic_updates if uses_simple_game else 0),  # Include delegated atomic publication.
                "simple_game_call_sites": simple_game_calls,  # Publish shared-core construction count.
                "reachable_definitions": reachability["definition_count"],  # Reconcile bounded package call graph.
                "multiworker_status": "blocked",  # Refuse second-worker authorization.
                "reason": "state_and_money_not_committed_by_one_cross_process_boundary",  # Name missing provider primitive.
            }
        )
    # Return deterministic catalog order.
    return sorted(rows, key=lambda row: row["game_id"])


# Build complete evidence from one exact checkout.
def build_inventory(repo_root: Path, commit: str | None = None) -> dict:
    # Resolve checkout provenance independently of caller assertions.
    checkout_commit = source_commit(repo_root)
    # Use exact checkout provenance when no explicit assertion is supplied.
    exact_commit = checkout_commit if commit is None else commit
    # Require one exact string identity.
    if not isinstance(exact_commit, str) or SOURCE_COMMIT_PATTERN.fullmatch(exact_commit) is None:
        # Reject malformed caller provenance.
        raise MultiprocessSafetyAuditError("source provenance unavailable")
    # Require explicit assertions to identify this checkout.
    if exact_commit != checkout_commit:
        # Reject syntactically valid source spoofing.
        raise MultiprocessSafetyAuditError("source provenance unavailable")
    # Reject any tracked or untracked checkout dirt before reading source bytes.
    require_clean_tree(repo_root)
    # Parse and hash every relevant production source and manifest.
    modules, manifests, tree_digest = _source_records(repo_root)
    # Build the exact source-path set.
    module_paths = {module["path"] for module in modules}
    # Load and validate every registered game.
    registered_games = _registered_games(manifests, module_paths)
    # Build the exact registered game-id set.
    game_ids = {game["game_id"] for game in registered_games}
    # Inventory every module-level lock, mutable container, cache, and singleton.
    module_state = _module_state_inventory(modules, game_ids)
    # Inventory every mutable instance attribute and lock.
    instance_state = _instance_state_inventory(modules)
    # Prove required control-plane paths semantically.
    components = _component_inventory(modules, module_state, instance_state)
    # Classify all registered game persistence paths semantically.
    games = _game_inventory(registered_games, modules)
    # Count all detailed blockers across every evidence family.
    blocker_count = sum(
        row["multiworker_status"] == "blocked"  # Count one explicit conservative disposition.
        for row in module_state + instance_state + components + games  # Reconcile all evidence families.
    )
    # Count detailed compatible state surfaces separately.
    compatible_count = sum(
        row["multiworker_status"] == "compatible"  # Count one reviewed compatible disposition.
        for row in module_state + instance_state + components + games  # Reconcile all evidence families.
    )
    # Return sanitized structural evidence only.
    return {
        "schema": SCHEMA,  # Publish the evidence contract version.
        "source_commit": exact_commit,  # Bind evidence to exact checkout HEAD.
        "analyzed_tree_sha256": tree_digest,  # Bind every analyzed source/manifest byte.
        "decision": "second_worker_blocked",  # Keep the checkpoint non-authorizing.
        "summary": {  # Publish only aggregate structural counts.
            "catalog_game_count": len(games),  # Reconcile all governed games.
            "module_state_count": len(module_state),  # Count module locks/globals/singletons.
            "instance_state_count": len(instance_state),  # Count instance locks/mutable state.
            "component_count": len(components),  # Count required control-plane surfaces.
            "blocker_count": blocker_count,  # Count every conservative blocker.
            "compatible_count": compatible_count,  # Count explicitly compatible surfaces.
        },
        "components": components,  # Retain exact control-plane proof.
        "games": games,  # Retain exact per-game proof.
        "module_state": module_state,  # Retain module global/singleton/cache proof.
        "instance_state": instance_state,  # Retain instance lock/mutable-state proof.
    }


# Execute the audit behind one fixed value-free CLI failure boundary.
def main() -> int:
    # Resolve the repository root from the tracked script.
    repo_root = Path(__file__).resolve().parents[1]
    # Run parsing, validation, and serialization inside the privacy boundary.
    try:
        # Build evidence only from a clean exact checkout.
        evidence = build_inventory(repo_root)
        # Serialize deterministic sanitized JSON before writing any output.
        rendered = json.dumps(evidence, indent=2, sort_keys=True)
    # Collapse every operational, parsing, serialization, and source error.
    except Exception:
        # Emit only the fixed value-free error.
        sys.stderr.write(CLI_FAILURE_MESSAGE + "\n")
        # Return one fixed nonzero status.
        return 1
    # Emit complete evidence only after every gate succeeds.
    sys.stdout.write(rendered + "\n")
    # Report successful inventory completion even though worker activation remains blocked.
    return 0


# Execute the standalone audit only when explicitly invoked.
if __name__ == "__main__":
    # Exit with the deterministic CLI status.
    sys.exit(main())
