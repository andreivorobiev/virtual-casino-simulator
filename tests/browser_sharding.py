# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Browser case discovery, affinity packing, and shard-evidence validation."""

# Inspect the runner function without executing any Browser case body.
import inspect
# Parse the reviewed inventory and duration profiles with strict JSON semantics.
import json
# Reject non-finite duration weights before they can influence shard ownership.
import math
# Discover literal Browser case registrations without maintaining executable duplicates.
import re
# Resolve tracked profiles and retained shard evidence independently of process cwd.
from pathlib import Path

# Declare producer/consumer case groups whose inline Browser state must stay on one shard.
BROWSER_CASE_AFFINITY_GROUPS = {
    # Keep the real backend login and service-worker lifecycle in one isolated context.
    "auth_backend_pwa": ("BR-AUTH-BACKEND-001", "BR-PWA-001", "BR-PWA-UPDATE-001"),
    # Keep the disposable guest lifecycle and closed-session refresh proof together.
    "guest_lifecycle": ("BR-GUEST-TRIAL-001", "BR-GUEST-REFRESH-001", "BR-GUEST-CONVERT-ANALYTICS-001"),
    # Keep login, terms, wallet, shell, catalog, and responsive lobby state together.
    "auth_lobby": ("BR-STATIC-CACHE-001", "BR-MARKETING-001", "BR-SHELL-BRAND-GUEST-001", "BR-OAUTH-001", "BR-OAUTH-SIGNUP-001", "BR-VERIFIED-EMAIL-001", "BR-TOUCH-TARGET-AUTH-001", "BR-AUTH-LOGIN-001", "BR-TERMS-001", "BR-AUTH-SHELL-001", "BR-OAUTH-RUNTIME-001", "BR-TOKEN-001", "BR-SEC-001", "BR-AUTH-LOCALE-001", "BR-AUTH-LOGOUT-001", "BR-TOKEN-FRACTION-001", "BR-SHELL-001", "BR-TOUCH-TARGET-001", "BR-SHELL-BRAND-001", "BR-TOKEN-WALLET-001", "BR-LOBBY-001", "BR-CATALOG-NAV-001", "BR-CATALOG-I18N-RU-001", "BR-LOBBY-RESP-001"),
    # Keep Roulette, autoplay, Slots, and Keno transitions under one state owner.
    "roulette_slots_keno": ("BR-ROU-HITMAP-001", "BR-ROU-REFUND-001", "BR-ROU-SLIP-AUDIT-001", "BR-ROU-PREMIUM-001", "BR-I18N-GAMESTATE-ROU-001", "BR-ROU-MOTION-CURVE-001", "BR-ROU-SPINNING-COPY-001", "BR-ROU-LOCKED-REMOVE-001", "BR-ROU-001", "BR-AUTO-START-FAIL-001", "BR-AUTO-ROU-001", "BR-ROU-REDUCED-MOTION-001", "BR-MONEY-LABEL-001", "BR-SLOTS-PAYLINE-001", "BR-SLOT-LINE-BET-001", "BR-SLOT-ECONOMICS-001", "BR-SLOT-001", "BR-KENO-EDGE-001", "BR-KENO-001"),
    # Keep Bingo, Blackjack, Baccarat, feedback, Admin, audio, and i18n state together.
    "bingo_admin": ("BR-BINGO-PURCHASE-001", "BR-BINGO-001", "BR-BJ-NATURAL-PAYOUT-001", "BR-BJ-001", "BR-BJ-I18N-001", "BR-BJ-INSURANCE-NET-001", "BR-BAC-COPY-001", "BR-BAC-FRESH-SHOE-001", "BR-BAC-MUTATION-001", "BR-BAC-001", "BR-I18N-ROUTES-001", "BR-WELLNESS-001", "BR-FEEDBACK-001", "BR-ADMIN-NAV-AUTH-001", "BR-ADMIN-001", "BR-ADMIN-DIAGNOSTICS-001", "BR-ADMIN-ECONOMICS-001", "BR-ADMIN-SESSION-POLICY-001", "BR-ADMIN-LEDGER-LABELS-001", "BR-ADMIN-FEEDBACK-001", "BR-ADMIN-OAUTH-001", "BR-ADMIN-MAIL-001", "BR-INVITE-001", "BR-OPS-001", "BR-ADMIN-PRACTICE-OPPONENT-001", "BR-ADMIN-USERS-001", "BR-ADMIN-GUEST-001", "BR-AUDIO-001", "BR-I18N-FOUNDATION-001", "BR-I18N-ADMIN-001"),
}

# Map each game to its one dedicated deep Browser case for affected-game selection.
BROWSER_GAME_ACCEPTANCE_CASES = {
    "acey_deucey": "BR-AD-001", "andar_bahar": "BR-AB-001", "big_six_wheel": "BR-BIG-SIX-001", "caribbean_stud": "BR-CS-001", "casino_holdem": "BR-CH-001", "casino_war": "BR-CW-001", "chuck_a_luck": "BR-CHUCK-001", "craps": "BR-CRAPS-001", "crown_and_anchor": "BR-CAA-001", "daily_draw_lab": "BR-DAILY-DRAW-LAB-001", "deuces_wild_video_poker": "BR-DWVP-001", "double_bonus_video_poker": "BR-DBVP-001", "dragon_tiger": "BR-DT-001", "fan_tan": "BR-FAN-TAN-001", "faro": "BR-FARO-001", "four_card_poker": "BR-FOUR-CARD-POKER-001", "hi_lo": "BR-HILO-001", "jacks_or_better_video_poker": "BR-JOBVP-001", "joker_poker": "BR-JP-001", "let_it_ride": "BR-LIR-001", "mississippi_stud": "BR-MSTUD-001", "multi_hand_video_poker": "BR-MHVP-001", "over_under_7": "BR-OU7-001", "pachinko": "BR-PACHINKO-001", "pai_gow_poker": "BR-PGP-001", "plinko": "BR-PLINKO-001", "red_dog": "BR-RD-001", "scratch_cards": "BR-SCRATCH-001", "sic_bo": "BR-SIC-BO-001", "teen_patti": "BR-TEEN-PATTI-001", "texas_holdem_practice_table": "BR-THPT-001", "three_card_poker": "BR-TCP-001", "trente_et_quarante": "BR-TEQ-001",
}

# Invert the acceptance map once so selection checks remain deterministic and constant-time.
BROWSER_ACCEPTANCE_CASE_GAME = {case_id: game_id for game_id, case_id in BROWSER_GAME_ACCEPTANCE_CASES.items()}
# Bound reviewed profile bytes so malformed evidence cannot consume unbounded memory.
BROWSER_DURATION_PROFILE_MAX_BYTES = 64 * 1024
# Bound one ordinary Browser case to the existing suite timeout budget.
BROWSER_DURATION_MAX_SECONDS = 3600
# Keep every hostile duration-profile failure value-free and path-independent.
BROWSER_DURATION_PROFILE_ERROR = "browser duration profile is invalid"
# Keep inventory drift diagnostics fixed so CI does not reflect attacker-controlled case text.
BROWSER_CASE_INVENTORY_ERROR = "browser case inventory does not match the reviewed baseline"


# Reject duplicate JSON object keys instead of accepting last-value-wins governance data.
def _unique_object(pairs, error_message):
    # Build one object only while every key remains unique.
    result = {}
    # Inspect each decoded pair without reflecting hostile values in diagnostics.
    for key, value in pairs:
        # Reject a duplicate key before it can overwrite reviewed evidence.
        if key in result:
            # Use the caller's fixed diagnostic for inventory and duration profiles alike.
            raise ValueError(error_message)
        # Retain the unique pair for structural validation.
        result[key] = value
    # Return the uniquely keyed object to the JSON decoder.
    return result


# List literal BR-prefixed registrations from the Browser runner and extracted owners in deterministic source order.
def discover_browser_case_ids(browser_runner, area_owners=None):
    # Read only the supplied Browser runner function from this checkout.
    source = inspect.getsource(browser_runner)
    # Normalize an omitted owner map without importing Browser case modules here.
    owners = dict(area_owners or {})
    # Build one ordered token expression for inline registrations and reviewed area-owner delegations.
    owner_pattern = "|".join(re.escape(owner_name) for owner_name in sorted(owners, key=lambda value: (-len(value), value)))
    # Match each literal inline registration and each exact area-owner call at its source position.
    token_pattern = re.compile(r"\brun_case\(\s*['\"](?P<case_id>BR-[A-Za-z0-9\-]+)['\"]" + (rf"|\b(?P<owner>{owner_pattern})\.run_cases\(" if owner_pattern else ""))
    # Retain the source-order identity stream without executing setup, listeners, or Browser code.
    case_ids = []
    # Expand every matched source token through exactly one controlled path.
    for match in token_pattern.finditer(source):
        # Append an inline permanent identity unchanged.
        if match.group("case_id"):
            case_ids.append(match.group("case_id"))
            continue
        # Read only the registered owner function source for the matched delegation alias.
        owner_source = inspect.getsource(owners[match.group("owner")])
        # Expand the owner's literal registrations in their exact internal source order.
        case_ids.extend(re.findall(r"\brun_case\(\s*['\"](BR-[A-Za-z0-9\-]+)['\"]", owner_source))
    # Return one deterministic cross-file identity stream for baseline and shard validation.
    return case_ids


# Load the reviewed count and sorted case-id list used by every extraction slice.
def load_browser_case_inventory(inventory_path):
    # Read bounded tracked bytes so missing or oversized governance data fails closed.
    try:
        # Keep the inventory well below the existing duration-profile ceiling.
        raw = Path(inventory_path).read_bytes()
    # Normalize every filesystem failure into one fixed diagnostic.
    except OSError:
        # Suppress host-specific path details from the failure.
        raise AssertionError(BROWSER_CASE_INVENTORY_ERROR) from None
    # Reject empty or unexpectedly large inventory evidence before decoding it.
    if not raw or len(raw) > BROWSER_DURATION_PROFILE_MAX_BYTES:
        # Preserve the same value-free failure at every parser boundary.
        raise AssertionError(BROWSER_CASE_INVENTORY_ERROR)
    # Parse strict UTF-8 JSON while rejecting duplicate object keys.
    try:
        # Bind the fixed inventory diagnostic into the duplicate-key hook.
        unique_hook = lambda pairs: _unique_object(pairs, BROWSER_CASE_INVENTORY_ERROR)
        # Decode exactly one checked-in JSON object.
        inventory = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_hook)
    # Normalize syntax, encoding, duplicate-key, and recursion failures.
    except (UnicodeDecodeError, ValueError, RecursionError):
        # Hide parser implementation details from the stable governance result.
        raise AssertionError(BROWSER_CASE_INVENTORY_ERROR) from None
    # Require the exact two-field packet so metadata cannot drift silently.
    if not isinstance(inventory, dict) or set(inventory) != {"count", "case_ids"}:
        # Reject extra policy controls and incomplete baselines alike.
        raise AssertionError(BROWSER_CASE_INVENTORY_ERROR)
    # Read the count and sorted identity list without coercion.
    count = inventory["count"]
    # Keep the reviewed ID sequence separate for structural checks.
    case_ids = inventory["case_ids"]
    # Require an exact nonnegative integer count and a string-only list.
    if type(count) is not int or count < 0 or not isinstance(case_ids, list) or not all(isinstance(case_id, str) for case_id in case_ids):
        # Reject booleans, coercible strings, and malformed list members.
        raise AssertionError(BROWSER_CASE_INVENTORY_ERROR)
    # Require one sorted, unique, BR-prefixed identity list whose count is self-consistent.
    if count != len(case_ids) or case_ids != sorted(case_ids) or len(case_ids) != len(set(case_ids)) or any(not re.fullmatch(r"BR-[A-Za-z0-9\-]+", case_id) for case_id in case_ids):
        # Fail before sharding can use incomplete or duplicated ownership inputs.
        raise AssertionError(BROWSER_CASE_INVENTORY_ERROR)
    # Return immutable inventory evidence to prevent accidental test mutation.
    return count, tuple(case_ids)


# Require current source discovery to equal the reviewed pre-slice count and sorted identity list.
def validate_browser_case_inventory(case_ids, inventory_path):
    # Load the checked-in comparison packet through strict parsing.
    expected_count, expected_ids = load_browser_case_inventory(inventory_path)
    # Reject duplicate source registrations independently of sorted-list comparison.
    if len(case_ids) != len(set(case_ids)):
        # Prevent duplicate IDs from satisfying a set-only oracle.
        raise AssertionError(BROWSER_CASE_INVENTORY_ERROR)
    # Compare both required acceptance dimensions: exact count and exact sorted IDs.
    if len(case_ids) != expected_count or tuple(sorted(case_ids)) != expected_ids:
        # Fail closed before any Browser listener or process starts.
        raise AssertionError(BROWSER_CASE_INVENTORY_ERROR)
    # Return the original source order used by deterministic sequence accounting.
    return list(case_ids)


# Load and strictly validate tracked per-case duration evidence.
def load_browser_case_durations(profile_path, case_ids):
    # Read bounded raw bytes so oversized or unreadable input fails with one fixed error.
    try:
        # Read only the supplied reviewed profile path.
        raw = Path(profile_path).read_bytes()
    # Normalize every filesystem failure without disclosing a path or host detail.
    except OSError:
        # Suppress the dynamic filesystem cause.
        raise AssertionError(BROWSER_DURATION_PROFILE_ERROR) from None
    # Reject an empty or oversized profile before decoding or parsing it.
    if not raw or len(raw) > BROWSER_DURATION_PROFILE_MAX_BYTES:
        # Preserve the historical fixed failure contract.
        raise AssertionError(BROWSER_DURATION_PROFILE_ERROR)
    # Decode and parse with duplicate-key and non-finite constant rejection.
    try:
        # Reject NaN and Infinity tokens before numeric validation.
        reject_constant = lambda _token: (_ for _ in ()).throw(ValueError(BROWSER_DURATION_PROFILE_ERROR))
        # Bind the duration diagnostic into the duplicate-key hook.
        unique_hook = lambda pairs: _unique_object(pairs, BROWSER_DURATION_PROFILE_ERROR)
        # Parse only the reviewed UTF-8 JSON object.
        profile = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_hook, parse_constant=reject_constant)
    # Normalize every syntax, Unicode, recursion, or duplicate-key failure.
    except (UnicodeDecodeError, ValueError, RecursionError):
        # Suppress dynamic parser causes just like the legacy runner.
        raise AssertionError(BROWSER_DURATION_PROFILE_ERROR) from None
    # Require one bounded object rather than lists, scalars, or excessive rows.
    if not isinstance(profile, dict) or len(profile) > len(case_ids):
        # Fail before unknown weights can affect ownership.
        raise AssertionError(BROWSER_DURATION_PROFILE_ERROR)
    # Resolve the current literal inventory so stale or invented keys cannot bias the median.
    known_cases = set(case_ids)
    # Build normalized whole-second weights only after every row passes.
    durations = {}
    # Validate each profile row without reflecting its key or value.
    for case_id, value in profile.items():
        # Require a literal current case identifier.
        if not isinstance(case_id, str) or case_id not in known_cases:
            # Reject stale or invented duration ownership.
            raise AssertionError(BROWSER_DURATION_PROFILE_ERROR)
        # Validate exact integers without lossy float coercion.
        if type(value) is int:
            # Reject nonpositive and overflow weights rather than clamping them.
            if value < 1 or value > BROWSER_DURATION_MAX_SECONDS:
                # Keep the hostile-value diagnostic fixed.
                raise AssertionError(BROWSER_DURATION_PROFILE_ERROR)
        # Validate exact floats separately so only finite values reach bounds.
        elif type(value) is float:
            # Reject non-finite, nonpositive, and overflow float weights.
            if not math.isfinite(value) or value < 1 or value > BROWSER_DURATION_MAX_SECONDS:
                # Keep the hostile-value diagnostic fixed.
                raise AssertionError(BROWSER_DURATION_PROFILE_ERROR)
        # Reject booleans, strings, containers, and every other JSON type.
        else:
            # Preserve strict type semantics from the pre-extraction runner.
            raise AssertionError(BROWSER_DURATION_PROFILE_ERROR)
        # Retain one deterministic rounded whole-second weight.
        durations[case_id] = round(value)
    # Return the validated partial profile; unmeasured cases use the median below.
    return durations


# Compute deterministic duration-balanced case ownership for one shard count.
def pack_browser_shards(case_ids, durations, shard_count, affinity_groups=BROWSER_CASE_AFFINITY_GROUPS):
    # Weigh unmeasured cases at the reviewed profile median until new evidence is generated.
    default = sorted(durations.values())[len(durations) // 2] if durations else 1
    # Collect every producer/consumer case whose stateful group must remain indivisible.
    grouped = {case_id for group_case_ids in affinity_groups.values() for case_id in group_case_ids}
    # Build each declared affinity group as one atomic weighted pack item.
    items = [(tuple(group_case_ids), sum(durations.get(case_id, default) for case_id in group_case_ids)) for group_case_ids in affinity_groups.values()]
    # Append every ungrouped literal case as its own weighted item.
    items += [((case_id,), durations.get(case_id, default)) for case_id in case_ids if case_id not in grouped]
    # Start every requested shard with an empty owned set and zero load.
    loads = [0] * shard_count
    # Keep mutable ownership sets only during deterministic packing.
    owned = [set() for _ in range(shard_count)]
    # Assign heaviest items first, with case ID and shard index as deterministic tie breakers.
    for members, weight in sorted(items, key=lambda item: (-item[1], item[0][0])):
        # Select the currently lightest shard deterministically.
        target = min(range(shard_count), key=lambda index: (loads[index], index))
        # Add this indivisible item's reviewed weight to its owner.
        loads[target] += weight
        # Record every grouped member under the same owner.
        owned[target].update(members)
    # Return immutable declarations for execution and aggregate evidence.
    return [frozenset(shard_cases) for shard_cases in owned]


# Report whether one active ownership set executes a named case.
def shard_owns(owned_cases, case_id):
    # Treat unsharded runs as owning every case.
    if owned_cases is None:
        # Preserve the historical unsharded runner contract.
        return True
    # Report membership in this shard's validated packed ownership.
    return case_id in owned_cases


# Report whether one active ownership set contains every member of an affinity group.
def shard_owns_group(owned_cases, group_name, affinity_groups=BROWSER_CASE_AFFINITY_GROUPS):
    # Treat unsharded runs as owning every affinity group.
    if owned_cases is None:
        # Preserve the historical unsharded runner contract.
        return True
    # Resolve the declared group and fail closed on an unknown ownership label.
    case_ids = affinity_groups[group_name]
    # Require the active packed shard to own every case sharing inline state.
    return all(case_id in owned_cases for case_id in case_ids)


# Validate affinity identities and exact partition ownership before Browser startup.
def validate_browser_shard_affinity(case_ids, shard_sets, affinity_groups=BROWSER_CASE_AFFINITY_GROUPS):
    # Reject duplicated case IDs because packed ownership would otherwise be ambiguous.
    if len(case_ids) != len(set(case_ids)):
        # Preserve the existing focused duplicate diagnostic.
        raise AssertionError("duplicate browser case ids prevent deterministic sharding")
    # Require exact union and nonduplication before any listener or Browser process starts.
    if sorted(case_id for shard_cases in shard_sets for case_id in shard_cases) != sorted(case_ids):
        # Reject missing, invented, or multiply owned cases.
        raise AssertionError("browser shard packing does not partition the literal case inventory")
    # Validate every named producer/consumer group against source identity and ownership.
    for group_name, group_case_ids in affinity_groups.items():
        # Reject missing or repeated group members rather than weakening affinity.
        if len(group_case_ids) != len(set(group_case_ids)) or any(case_id not in case_ids for case_id in group_case_ids):
            # Identify only the reviewed group name in the failure.
            raise AssertionError(f"invalid browser affinity group {group_name}")
        # Resolve the one deterministic packed owner for every group member.
        owners = {index for index, shard_cases in enumerate(shard_sets) for case_id in group_case_ids if case_id in shard_cases}
        # Fail startup when a producer/consumer group would cross a shard boundary.
        if len(owners) != 1:
            # Retain deterministic owner indexes for diagnosis.
            raise AssertionError(f"browser affinity group {group_name} crosses shards {sorted(owners)}")


# Validate the game-to-case map against the exact catalog and source inventory.
def validate_browser_affected_games(case_ids, catalog_ids, affinity_groups=BROWSER_CASE_AFFINITY_GROUPS, game_cases=BROWSER_GAME_ACCEPTANCE_CASES):
    # Flatten declared affinity cases so dedicated deselection cannot bypass shared state.
    affinity_case_ids = {case_id for group_case_ids in affinity_groups.values() for case_id in group_case_ids}
    # Reject a map pairing two games with one case because selection would be ambiguous.
    if len(set(game_cases.values())) != len(game_cases):
        # Preserve the existing focused mapping diagnostic.
        raise AssertionError("duplicate dedicated acceptance case in affected-game map")
    # Reject any dedicated case also owned by a stateful affinity group.
    if set(game_cases.values()) & affinity_case_ids:
        # Prevent partial group deselection from breaking producer/consumer state.
        raise AssertionError("affected-game map contains an affinity-owned browser case")
    # Require every mapped game and case to still exist.
    for game_id, case_id in game_cases.items():
        # Fail closed on an unknown catalog game ID.
        if game_id not in catalog_ids:
            # Keep the reviewed game identity in the deterministic diagnostic.
            raise AssertionError(f"affected-game map references unknown game {game_id}")
        # Fail closed when a mapped case is absent from source discovery.
        if case_id not in case_ids:
            # Keep the reviewed case identity in the deterministic diagnostic.
            raise AssertionError(f"affected-game case {case_id} absent from browser inventory")


# Report whether detector-owned game selection excludes one dedicated case.
def case_deselected(case_id, affected_games, acceptance_case_game=BROWSER_ACCEPTANCE_CASE_GAME):
    # Keep every case when no affected-game restriction is active.
    if affected_games is None:
        # Preserve full coverage for main, shared, unknown, and manual inputs.
        return False
    # Skip only dedicated cases whose game is outside the detector-owned set.
    return case_id in acceptance_case_game and acceptance_case_game[case_id] not in affected_games


# List source-ordered cases one ownership set executes after game deselection.
def selected_case_ids(case_ids, owned_cases, affected_games):
    # Keep only owned cases that survive affected-game deselection.
    return [case_id for case_id in case_ids if (owned_cases is None or case_id in owned_cases) and not case_deselected(case_id, affected_games)]


# Compute the exact source-ordered case IDs expected across all shards.
def expected_case_ids(case_ids, affected_games):
    # Return the full source inventory when no affected-game restriction applies.
    if affected_games is None:
        # Copy the caller list so downstream code cannot mutate discovery state.
        return list(case_ids)
    # Otherwise drop dedicated cases for games outside the detector-owned set.
    return [case_id for case_id in case_ids if not case_deselected(case_id, affected_games)]


# Verify retained shard evidence covers the detector-owned inventory exactly once.
def verify_browser_shards(results_dir, shard_count, affected_games, case_ids, expected_owned):
    # Track every observed Browser case and the shard that executed it.
    seen = {}
    # Track every shard's exact ownership declaration for union validation.
    declared_owned = {}
    # Canonicalize detector-owned selection rather than trusting shard artifacts.
    expected_declaration = sorted(affected_games) if affected_games else None
    # Derive expected execution only from current source and detector input.
    expected = expected_case_ids(case_ids, affected_games)
    # Read each unique shard result and fail on missing evidence.
    for index in range(shard_count):
        # Resolve the exact filename created by the sharded Browser runner.
        path = Path(results_dir) / f"browser_results_shard_{index}_of_{shard_count}.json"
        # Fail closed when a shard left no retained packet.
        if not path.exists():
            # Preserve the historical aggregate diagnostic.
            print(f"BROWSER_SHARDS FAIL missing shard result file {path}")
            # Return a failing CLI status without raising dynamic parser text.
            return 1
        # Parse bounded checked-in-style JSON evidence.
        try:
            # Decode the complete shard packet as UTF-8 JSON.
            data = json.loads(path.read_text(encoding="utf-8"))
        # Reject unreadable or malformed evidence uniformly.
        except (OSError, UnicodeDecodeError, ValueError):
            # Preserve the historical value-free shard diagnostic.
            print(f"BROWSER_SHARDS FAIL malformed shard result {index}")
            # Return a failing aggregate status.
            return 1
        # Require one object before reading its declaration.
        if not isinstance(data, dict):
            # Reject scalar and list packets.
            print(f"BROWSER_SHARDS FAIL malformed shard result {index}")
            # Return a failing aggregate status.
            return 1
        # Bind packet identity to filename and requested matrix.
        if type(data.get("shard_index")) is not int or data.get("shard_index") != index or type(data.get("shard_count")) is not int or data.get("shard_count") != shard_count:
            # Reject forged or stale worker identity.
            print(f"BROWSER_SHARDS FAIL shard {index} identity mismatch")
            # Return a failing aggregate status.
            return 1
        # Reject a shard whose detector selection differs from aggregate input.
        if data.get("affected_games") != expected_declaration:
            # Retain the mismatch needed for hosted diagnosis.
            print(f"BROWSER_SHARDS FAIL shard {index} affected games {data.get('affected_games')} != expected {expected_declaration}")
            # Return a failing aggregate status.
            return 1
        # Require one sorted unique string ownership declaration.
        owned = data.get("owned_cases")
        # Reject missing, malformed, duplicated, or reordered ownership.
        if not isinstance(owned, list) or not all(isinstance(case_id, str) for case_id in owned) or len(owned) != len(set(owned)) or owned != sorted(owned):
            # Preserve the fixed declaration diagnostic.
            print(f"BROWSER_SHARDS FAIL shard {index} has invalid owned_cases")
            # Return a failing aggregate status.
            return 1
        # Require this declaration to equal deterministic governed packing.
        if owned != sorted(expected_owned[index]):
            # Reject forged, stale, or partial ownership.
            print(f"BROWSER_SHARDS FAIL shard {index} owned_cases mismatch")
            # Return a failing aggregate status.
            return 1
        # Retain exact ownership for pairwise-disjoint union checks.
        declared_owned[index] = set(owned)
        # Require a result collection before inspecting Browser rows.
        if not isinstance(data.get("results"), list):
            # Reject a packet with no iterable evidence rows.
            print(f"BROWSER_SHARDS FAIL malformed shard result {index}")
            # Return a failing aggregate status.
            return 1
        # Examine only Browser-suite records so mixed runs cannot confuse coverage.
        for result in data["results"]:
            # Require each retained row to expose string identity and status.
            if not isinstance(result, dict) or not isinstance(result.get("test_id"), str) or not isinstance(result.get("status"), str):
                # Reject malformed evidence before prefix filtering.
                print(f"BROWSER_SHARDS FAIL malformed row in shard {index}")
                # Return a failing aggregate status.
                return 1
            # Ignore non-Browser records defensively without counting them.
            if not result["test_id"].startswith("BR-"):
                # Continue to the next retained result row.
                continue
            # Reject a Browser row its producing shard does not own.
            if result["test_id"] not in declared_owned[index]:
                # Report the reviewed test identity and producing shard.
                print(f"BROWSER_SHARDS FAIL shard {index} reported unowned case {result['test_id']}")
                # Return a failing aggregate status.
                return 1
            # Fail closed when any retained Browser case is non-passing.
            if result["status"] != "PASS":
                # Preserve the exact failing case and shard for diagnosis.
                print(f"BROWSER_SHARDS FAIL non-passing case {result['test_id']} in shard {index}")
                # Return a failing aggregate status.
                return 1
            # Reject duplicate execution across two shards.
            if result["test_id"] in seen:
                # Report both owners of the duplicated case.
                print(f"BROWSER_SHARDS FAIL duplicate case {result['test_id']} in shards {seen[result['test_id']]} and {index}")
                # Return a failing aggregate status.
                return 1
            # Record this case's producing shard for exact-union validation.
            seen[result["test_id"]] = index
    # Require pairwise-disjoint ownership declarations.
    if sum(len(shard_cases) for shard_cases in declared_owned.values()) != len(set().union(*declared_owned.values())):
        # Reject overlap even when result rows happen to be unique.
        print("BROWSER_SHARDS FAIL declared shard ownerships overlap")
        # Return a failing aggregate status.
        return 1
    # Require the declared union to equal current source inventory.
    if set().union(*declared_owned.values()) != set(case_ids):
        # Reject missing or invented ownership before checking execution rows.
        print("BROWSER_SHARDS FAIL declared shard ownerships do not partition the case inventory")
        # Return a failing aggregate status.
        return 1
    # Collect every expected case absent from retained results.
    missing = [case_id for case_id in expected if case_id not in seen]
    # Fail closed on incomplete execution coverage.
    if missing:
        # Preserve exact missing reviewed identities for hosted diagnosis.
        print(f"BROWSER_SHARDS FAIL missing cases {missing}")
        # Return a failing aggregate status.
        return 1
    # Collect executed cases not present in detector-owned expectations.
    extra = sorted(set(seen) - set(expected))
    # Fail closed on unexpected execution.
    if extra:
        # Preserve exact extra reviewed identities for hosted diagnosis.
        print(f"BROWSER_SHARDS FAIL unexpected cases {extra}")
        # Return a failing aggregate status.
        return 1
    # Print exact verified coverage for workflow logs.
    print(f"BROWSER_SHARDS VERIFIED cases={len(expected)} shards={shard_count}")
    # Return the historical successful CLI status.
    return 0
