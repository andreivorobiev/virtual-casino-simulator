# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import finite-number checks so the public stake boundary rejects NaN and infinity.
import math
import random
from casino.core.ids import new_id
from casino.core.clock import utc_now
from casino.errors import ValidationError

# Set GAME_ID to the value needed for the next operation.
GAME_ID = "slots"
# Pick reel stops from OS entropy so spin outcomes cannot be predicted from seedable process state. (issue #420)
_rng = random.SystemRandom()
# Set SYMBOLS to the value needed for the next operation.
SYMBOLS = ["CHERRY", "LEMON", "BAR", "BELL", "SEVEN", "WILD", "SCATTER"]
# Set REELS to the value needed for the next operation.
REELS = [
    ["CHERRY","LEMON","BAR","CHERRY","BELL","LEMON","WILD","BAR","CHERRY","SEVEN","LEMON","SCATTER","BELL","BAR"],
    ["LEMON","CHERRY","BAR","BELL","LEMON","WILD","CHERRY","BAR","SEVEN","LEMON","BELL","SCATTER","BAR","CHERRY"],
    ["BAR","LEMON","CHERRY","BELL","WILD","LEMON","BAR","CHERRY","SEVEN","SCATTER","BELL","LEMON","BAR","CHERRY"],
    ["CHERRY","BAR","LEMON","BELL","CHERRY","WILD","BAR","LEMON","SEVEN","BELL","SCATTER","CHERRY","BAR","LEMON"],
    ["LEMON","CHERRY","BAR","WILD","BELL","LEMON","CHERRY","BAR","SEVEN","SCATTER","BELL","LEMON","BAR","CHERRY"],
]
# Set PAYLINES to the value needed for the next operation.
PAYLINES = {
    1: [[1,1,1,1,1]],
    3: [[1,1,1,1,1],[0,0,0,0,0],[2,2,2,2,2]],
    5: [[1,1,1,1,1],[0,0,0,0,0],[2,2,2,2,2],[0,1,2,1,0],[2,1,0,1,2]],
    9: [[1,1,1,1,1],[0,0,0,0,0],[2,2,2,2,2],[0,1,2,1,0],[2,1,0,1,2],[0,0,1,2,2],[2,2,1,0,0],[1,0,1,2,1],[1,2,1,0,1]],
    20: [[1,1,1,1,1],[0,0,0,0,0],[2,2,2,2,2],[0,1,2,1,0],[2,1,0,1,2],[0,0,1,2,2],[2,2,1,0,0],[1,0,1,2,1],[1,2,1,0,1],[0,1,1,1,0],[2,1,1,1,2],[1,0,0,0,1],[1,2,2,2,1],[0,1,0,1,0],[2,1,2,1,2],[0,2,0,2,0],[2,0,2,0,2],[1,0,2,0,1],[1,2,0,2,1],[0,2,1,0,2]],
}
# Line-pay multipliers rebalance the real shipped reels to the approved house-side band. (SLOT-036)
PAYTABLE = {
    # Preserve a low-paying CHERRY family while removing the old player-positive return.
    "CHERRY": {3: 2, 4: 8, 5: 30},
    # Preserve a low-paying LEMON family while removing the old player-positive return.
    "LEMON": {3: 2, 4: 6, 5: 23},
    # Preserve the middle BAR family with proportionate three-, four-, and five-kind prices.
    "BAR": {3: 3, 4: 13, 5: 56},
    # Preserve the middle BELL family with proportionate three-, four-, and five-kind prices.
    "BELL": {3: 4, 4: 23, 5: 94},
    # Preserve SEVEN as the highest ordinary symbol while the jackpot remains additive.
    "SEVEN": {3: 11, 4: 112, 5: 450},
    # Preserve WILD substitution and a positive five-kind price for every-payline evidence.
    "WILD": {3: 9, 4: 75, 5: 300},
}
# Pay only four and five visible scatters because three scatters already award the feature.
SCATTER_PAYS = {4: 1, 5: 5}
# Keep the historical three-scatter feature trigger on the unchanged reel strips.
FREE_SPIN_SCATTER_THRESHOLD = 3
# Limit each trigger to four spins so retriggered bonus chains remain convergent.
FREE_SPINS_AWARDED = 4
# Seed and reset the one bounded progressive meter at two hundred play tokens.
PROGRESSIVE_SEED = 200.0
# Contribute exactly one percent of paid wagers and never contribute from zero-cost free spins.
PROGRESSIVE_RATE = 0.01
# Qualify exactly the disclosed maximum line choice so no other accepted line count can build or win the meter.
PROGRESSIVE_QUALIFYING_LINES = 20
# Qualify exactly the disclosed one-token line bet so accepted low/high stakes cannot build or win the meter.
PROGRESSIVE_QUALIFYING_LINE_BET = 1.0
# Preserve the frozen v1 minimum already accepted by the shared amount validator.
MIN_LINE_BET = 0.01
# Preserve the frozen v1 maximum already accepted by the shared amount validator.
MAX_LINE_BET = 1_000_000
# Bind an untraceable pre-upgrade free-spin bank to the minimum legal basis rather than trusting an escalation request.
LEGACY_FREE_SPIN_FALLBACK_BASIS = {"active_lines": 1, "line_bet": MIN_LINE_BET}

# Define the default_state function used by this module.
def default_state():
    # Seed one constant-size meter bound to the exact twenty-line, one-token qualifier.
    return {"last_spins": [], "progressive": PROGRESSIVE_SEED, "progressive_basis": {"active_lines": PROGRESSIVE_QUALIFYING_LINES, "line_bet": PROGRESSIVE_QUALIFYING_LINE_BET}, "free_spins": 0}

# Normalize the server-owned cent-token line-bet domain shared by engine and API callers.
def normalize_line_bet(value):
    # Reject booleans because Python otherwise treats them as numeric one and zero.
    if isinstance(value, bool):
        # Publish a stable domain error without reflecting the caller-controlled value.
        raise ValidationError(f"line_bet must be from {MIN_LINE_BET} to {MAX_LINE_BET}")
    # Protect numeric conversion so malformed bodies use the standard validation envelope.
    try:
        # Convert strings and JSON numbers before checking finiteness and the two-decimal money domain.
        line_bet = float(value)
    # Translate only expected conversion failures into the stable public error.
    except (TypeError, ValueError, OverflowError):
        # Publish a stable domain error without reflecting the caller-controlled value.
        raise ValidationError(f"line_bet must be from {MIN_LINE_BET} to {MAX_LINE_BET}")
    # Round through the existing two-decimal money contract before enforcing its frozen bounds.
    normalized = round(line_bet, 2)
    # Require one finite accepted amount and reject values that collapse below the minimum.
    if not math.isfinite(line_bet) or normalized < MIN_LINE_BET or normalized > MAX_LINE_BET:
        # Publish the complete legal domain so old and new clients can correct input.
        raise ValidationError(f"line_bet must be from {MIN_LINE_BET} to {MAX_LINE_BET}")
    # Return the two-decimal amount already accepted by the frozen v1 route.
    return normalized

# Report whether one normalized line/stake pair matches the only progressive qualifier.
def progressive_eligible(active_lines, line_bet):
    # Require both exact server-owned fields so stake or line switching cannot transfer meter value.
    return normalize_active_lines(active_lines) == PROGRESSIVE_QUALIFYING_LINES and normalize_line_bet(line_bet) == PROGRESSIVE_QUALIFYING_LINE_BET

# Normalize one persisted progressive value or replace it with the fixed qualifying seed.
def safe_progressive_value(value):
    # Start with the disclosed fixed qualifying-meter seed.
    seed = PROGRESSIVE_SEED
    # Convert a persisted number without losing fractional-cent contribution precision.
    try:
        # Read the candidate meter as a floating-point JSON number.
        meter = float(value)
    # Recover malformed state through the declared fixed seed.
    except (TypeError, ValueError, OverflowError):
        # Return the safe seed when conversion is impossible.
        return seed
    # Reject non-finite or non-positive state before payout calculations.
    if not math.isfinite(meter) or meter <= 0:
        # Return the safe seed for hostile or corrupt persisted values.
        return seed
    # Preserve eight-decimal internal precision for one-cent contribution accumulation.
    return round(meter, 8)

# Normalize every historical representation into one constant-size progressive state.
def progressive_meter(state):
    # Prefer the frozen scalar because it is the only field old clients and releases understood.
    candidate = state.get("progressive")
    # Inspect a transient basis map only when a prior controller build wrote one before publication.
    historical_meters = state.get("progressive_meters") if isinstance(state.get("progressive_meters"), dict) else {}
    # Recover the exact qualifier key when the scalar is missing or malformed.
    if candidate is None:
        # Prefer either earlier exact qualifier spelling without retaining caller-controlled keys.
        candidate = historical_meters.get("20:1.00", historical_meters.get("20"))
    # Normalize or safely seed the single authoritative meter.
    meter = safe_progressive_value(candidate)
    # Persist the one canonical scalar understood by existing clients.
    state["progressive"] = meter
    # Pin its fixed qualifier so state and runtime config remain self-describing.
    state["progressive_basis"] = {"active_lines": PROGRESSIVE_QUALIFYING_LINES, "line_bet": PROGRESSIVE_QUALIFYING_LINE_BET}
    # Delete any transient map so arbitrary legal stake cycling can never grow durable state.
    state.pop("progressive_meters", None)
    # Return the one retained value used by every qualifying spin.
    return meter

# Persist one updated value without introducing caller-controlled meter identities.
def store_progressive_meter(state, value):
    # Normalize the updated meter before retaining it.
    meter = safe_progressive_value(value)
    # Keep the frozen scalar field synchronized with the one qualifying meter.
    state["progressive"] = meter
    # Preserve the fixed qualifier beside the scalar for API and browser evidence.
    state["progressive_basis"] = {"active_lines": PROGRESSIVE_QUALIFYING_LINES, "line_bet": PROGRESSIVE_QUALIFYING_LINE_BET}
    # Delete any transient map so the persisted state remains constant-size.
    state.pop("progressive_meters", None)
    # Return the persisted meter used by response evidence.
    return meter

# Publish a detached, JSON-safe economics snapshot for the additive runtime config.
def economics_config():
    # Return copies so a caller cannot mutate the authoritative module tables.
    return {
        "scatter_pays": dict(SCATTER_PAYS),  # Publish the authoritative count-to-multiplier table.
        "free_spin_scatter_threshold": FREE_SPIN_SCATTER_THRESHOLD,  # Publish the feature trigger threshold.
        "free_spins_awarded": FREE_SPINS_AWARDED,  # Publish the authoritative bonus award.
        "progressive_seed": PROGRESSIVE_SEED,  # Publish the single meter seed and reset value.
        "progressive_rate": PROGRESSIVE_RATE,  # Publish the paid qualifier contribution rate.
        "progressive_qualifying_lines": PROGRESSIVE_QUALIFYING_LINES,  # Publish the exact line qualifier.
        "progressive_qualifying_line_bet": PROGRESSIVE_QUALIFYING_LINE_BET,  # Publish the exact stake qualifier.
        "progressive_basis_policy": "single_exact_qualifier",  # Publish the constant-size meter policy.
        "progressive_meter_limit": 1,  # Publish the persistent meter cardinality bound.
        "line_bet": {"api_minimum": MIN_LINE_BET, "api_maximum": MAX_LINE_BET, "ui_minimum": MIN_LINE_BET, "ui_maximum": MAX_LINE_BET, "ui_step": 0.01},  # Publish the cent-normalized frozen-v1 domain.
    }

# Normalize the exact closed set of supported line counts.
def normalize_active_lines(value):
    # Reject booleans because Python otherwise treats them as numeric one and zero.
    if isinstance(value, bool):
        # Publish the complete fixed line-count vocabulary.
        raise ValidationError("active_lines must be one of 1,3,5,9,20")
    # Protect integer conversion so malformed bodies receive the standard validation envelope.
    try:
        # Convert existing numeric strings and JSON integers exactly as the historical route did.
        active_lines = int(value)
    # Translate expected conversion failures without reflecting caller data.
    except (TypeError, ValueError, OverflowError):
        # Publish the complete fixed line-count vocabulary.
        raise ValidationError("active_lines must be one of 1,3,5,9,20")
    # Reject unsupported or fractional numeric inputs after integer conversion.
    if active_lines not in PAYLINES or isinstance(value, float) and value != active_lines:
        # Publish the complete fixed line-count vocabulary.
        raise ValidationError("active_lines must be one of 1,3,5,9,20")
    # Return the supported integer line count.
    return active_lines

# Recover a trusted paid-trigger basis for one pre-upgrade free-spin bank.
def trusted_bonus_basis(state):
    # Reuse an already persisted server-owned basis only when both fields validate.
    stored = state.get("free_spin_basis") if isinstance(state.get("free_spin_basis"), dict) else {}
    # Validate the stored line count and stake without consulting a consuming request.
    try:
        # Return the normalized persisted basis when it is complete and valid.
        # Preserve the stored eligibility only when it agrees with the locked paid-trigger stake.
        line_bet = normalize_line_bet(stored["line_bet"])
        # Return the normalized persisted basis and its server-derived progressive qualification.
        # Normalize the trusted line count once for the exact two-field qualifier check.
        active_lines = normalize_active_lines(stored["active_lines"])
        # Return only the normalized paid-trigger basis used for ordinary free-spin settlement.
        return {"active_lines": active_lines, "line_bet": line_bet}
    # Continue to deterministic migration when the stored basis is absent or corrupt.
    except (KeyError, ValidationError, TypeError, ValueError):
        # Ignore only the unusable private basis and inspect prior server-owned spin evidence next.
        pass
    # Search newest-first for the paid spin that originally awarded the still-open feature.
    for prior in reversed(state.get("last_spins", []) if isinstance(state.get("last_spins"), list) else []):
        # Skip rows that did not award free spins or were themselves free consumption.
        if not isinstance(prior, dict) or int(prior.get("free_spins_awarded", 0) or 0) <= 0 or bool(prior.get("free_spin")):
            # Continue until a paid trigger row is found.
            continue
        # Validate the server-owned historical basis before adopting it.
        try:
            # Return the exact paid trigger's legal line count and cent-normalized stake.
            # Normalize the trusted paid-trigger stake once.
            line_bet = normalize_line_bet(prior["line_bet"])
            # Return its exact line/stake basis and server-derived progressive qualification.
            # Normalize the trusted historical line count once for qualification.
            active_lines = normalize_active_lines(prior["active_lines"])
            # Return only its exact line/stake basis for ordinary free-spin settlement.
            return {"active_lines": active_lines, "line_bet": line_bet}
        # Ignore malformed legacy history and continue to the fail-safe floor.
        except (KeyError, ValidationError, TypeError, ValueError):
            # Continue searching older trusted rows before using the conservative fallback.
            continue
    # Bind untraceable legacy banks to the legal minimum so a consuming request can never escalate them.
    # Copy the conservative floor without granting any feature-spin progressive eligibility.
    return dict(LEGACY_FREE_SPIN_FALLBACK_BASIS)

# Resolve the actual paid or bonus-bound configuration without mutating entropy.
def effective_configuration(state, active_lines, line_bet):
    # Normalize the submitted line count before consulting feature state.
    requested_lines = normalize_active_lines(active_lines)
    # Normalize the submitted stake at the frozen v1 precision and bounds.
    requested_bet = normalize_line_bet(line_bet)
    # Detect an already banked free-spin chain.
    free = int(state.get("free_spins", 0)) > 0
    # Resolve a banked chain only from persisted server-owned trigger evidence.
    locked_basis = trusted_bonus_basis(state) if free else {}
    # Resolve a banked chain to its paid-trigger line count without trusting the consuming request.
    effective_lines = normalize_active_lines(locked_basis.get("active_lines", requested_lines)) if free else requested_lines
    # Resolve a banked chain to its paid-trigger stake without trusting the consuming request.
    effective_bet = normalize_line_bet(locked_basis.get("line_bet", requested_bet)) if free else requested_bet
    # Calculate the exact debit preview without changing bonus bank, meter, history, or RNG.
    cost = 0.0 if free else round(effective_lines * effective_bet, 2)
    # Make every free action categorically ineligible; only a paid exact qualifier can touch the meter.
    eligibility = False if free else progressive_eligible(effective_lines, effective_bet)
    # Return submitted and authoritative values for API, tests, and response diagnostics.
    return {"requested_active_lines": requested_lines, "requested_line_bet": requested_bet, "active_lines": effective_lines, "line_bet": effective_bet, "progressive_eligible": eligibility, "free_spin": free, "cost": cost}

# Define the render_grid function used by this module.
def render_grid(stops):
    # Set grid to the value needed for the next operation.
    grid = [[], [], []]
    for reel, stop in zip(REELS, stops):
        # Set L to the value needed for the next operation.
        L = len(reel)
        # Set symbols to the value needed for the next operation.
        symbols = [reel[(stop-1)%L], reel[stop%L], reel[(stop+1)%L]]
        # Iterate through the three visible rows for this reel.
        for r in range(3):
            # Append exactly one symbol from this reel to each visible row.
            grid[r].append(symbols[r])
    return grid

# Define the evaluate function used by this module.
def evaluate(grid, active_lines, line_bet):
    if active_lines not in PAYLINES:
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("active_lines must be one of 1,3,5,9,20")
    # Collect authoritative win rows and the independently reconcilable line return.
    wins=[]; line_payout=0.0
    for idx,line in enumerate(PAYLINES[active_lines]):
        # Set seq to the value needed for the next operation.
        seq = [grid[row][col] for col,row in enumerate(line)]
        # Set base to the value needed for the next operation.
        base = next((s for s in seq if s not in ("WILD", "SCATTER")), seq[0])
        # Set count to the value needed for the next operation.
        count=0
        for s in seq:
            if s == base or s == "WILD": count += 1
            # Handle the fallback branch when prior conditions did not match.
            else: break
        # Set mult to the value needed for the next operation.
        mult = PAYTABLE.get(base, {}).get(count, 0)
        if mult:
            # Set payout to the value needed for the next operation.
            payout = round(mult*line_bet,2); line_payout += payout
            wins.append({"line_index": idx, "line": line, "sequence": seq, "symbol": base, "count": count, "multiplier": mult, "payout": payout})
    # Set scatter_count to the value needed for the next operation.
    scatter_count = sum(1 for row in grid for s in row if s == "SCATTER")
    # Award the feature from the one declared server-owned scatter threshold and count.
    free_spins_awarded = FREE_SPINS_AWARDED if scatter_count >= FREE_SPIN_SCATTER_THRESHOLD else 0
    # Price visible scatters from the same authoritative table published to the API and browser.
    scatter_payout = round(line_bet * SCATTER_PAYS.get(scatter_count, 0), 2)
    if scatter_payout:
        wins.append({"scatter_count": scatter_count, "symbol":"SCATTER", "payout": scatter_payout, "kind":"scatter"})
    # Reconcile the complete non-progressive return from its two disjoint sources.
    payout = round(line_payout + scatter_payout, 2)
    # Return source components as additive evidence while preserving every existing field.
    return {"wins": wins, "payout": payout, "line_payout": round(line_payout, 2), "scatter_payout": scatter_payout, "scatter_count": scatter_count, "free_spins_awarded": free_spins_awarded}

# Define the spin function used by this module.
def spin(state, active_lines=5, line_bet=1.0, round_id=None):
    # Resolve paid or locked-bonus configuration without mutating state or drawing entropy.
    configuration = effective_configuration(state, active_lines, line_bet)
    # Adopt the authoritative line count selected by the paid or bonus basis.
    active_lines = configuration["active_lines"]
    # Adopt the authoritative two-decimal stake selected by the paid or bonus basis.
    line_bet = configuration["line_bet"]
    # Retain whether this spin consumes the already-banked feature.
    free = configuration["free_spin"]
    # Persist the resolved trusted basis before consuming any current or retriggered free spin.
    if free:
        # Retain the server-derived basis for the complete remaining feature chain.
        state["free_spin_basis"] = {"active_lines": active_lines, "line_bet": line_bet}
    # Set cost to the value needed for the next operation.
    cost = configuration["cost"]
    if free: state["free_spins"] = int(state.get("free_spins",0)) - 1
    # Draw each reel stop from the CSPRNG instance instead of the seedable module generator. (issue #420)
    stops = [_rng.randrange(len(r)) for r in REELS]
    # Set grid to the value needed for the next operation.
    grid = render_grid(stops)
    # Set result to the value needed for the next operation.
    result = evaluate(grid, active_lines, line_bet)
    if result["free_spins_awarded"]:
        # Set state["free_spins"] to the value needed for the next operation.
        state["free_spins"] = int(state.get("free_spins",0)) + result["free_spins_awarded"]
        # Pin a newly earned paid-spin feature to the configuration that paid for it.
        state["free_spin_basis"] = {"active_lines": active_lines, "line_bet": line_bet}
    # Remove a completed chain's basis so a later paid spin can select a new legal configuration.
    if int(state.get("free_spins", 0)) == 0:
        # Delete only the bonus basis after every awarded/retriggered spin has been consumed.
        state.pop("free_spin_basis", None)
    # Retain the pre-spin meter for exact progressive contribution and reset evidence.
    progressive_before = progressive_meter(state)
    # Compute the paid-only contribution independently from any payout source.
    progressive_contribution = round(cost * PROGRESSIVE_RATE, 8) if configuration["progressive_eligible"] and not free else 0.0
    # Apply the contribution before a same-spin jackpot, matching the historical settlement order.
    progressive_after_contribution = store_progressive_meter(state, progressive_before + progressive_contribution)
    # Default the additive jackpot component so every result reconciles without missing keys.
    result["progressive_hit"] = 0.0
    if not free and configuration["progressive_eligible"] and any(w.get("symbol") == "SEVEN" and w.get("count") == 5 for w in result["wins"]):
        # Set result["payout"] + to the value needed for the next operation.
        result["payout"] = round(result["payout"] + progressive_after_contribution, 2)
        # Set result["progressive_hit"] to the value needed for the next operation.
        result["progressive_hit"] = progressive_after_contribution
        # Reset the one authoritative meter to its fixed disclosed seed.
        store_progressive_meter(state, PROGRESSIVE_SEED)
    # Set round_id to the value needed for the next operation.
    round_id = round_id or new_id("slot")
    # Set spin_data to the value needed for the next operation.
    spin_data = {"round_id": round_id, "timestamp": utc_now(), "stops": stops, "grid": grid, "requested_active_lines": configuration["requested_active_lines"], "requested_line_bet": configuration["requested_line_bet"], "active_lines": active_lines, "line_bet": line_bet, "cost": cost, **result, "free_spin": free, "free_spins_remaining": state.get("free_spins",0), "progressive_eligible": configuration["progressive_eligible"], "progressive_basis": dict(state.get("progressive_basis", {})), "progressive_before": progressive_before, "progressive_contribution": progressive_contribution, "progressive": state.get("progressive")}
    state.setdefault("last_spins", []).append(spin_data)
    # Set state["last_spins"] to the value needed for the next operation.
    state["last_spins"] = state["last_spins"][-100:]
    return spin_data
