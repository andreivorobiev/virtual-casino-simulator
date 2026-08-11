# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Funded account allocation and controller metadata for practice opponents."""

# Import the public managed-account accounting seam.
from casino.core import practice_accounts
# Import stable validation errors for unsupported controller requests.
from casino.errors import ValidationError

# Identify the held game proposal that consumes this shared prerequisite.
TEXAS_HOLDEM_PRACTICE_GAME = "texas_holdem_practice_table"
# Allocate the existing named bot player accounts to the three practice seats.
PRACTICE_ACCOUNT_IDS = ("bot_1", "bot_2", "bot_3")
# Seed enough real play tokens for the maximum five-unit exposure in PR #120.
INITIAL_FUNDING = 100_000.0
# Publish the deterministic server policy expected by the held game slice.
CONTROLLER_POLICY = "practice_call"


# Validate the one game currently approved to use this account pool.
def require_game(game_id: str) -> str:
    # Reject unrelated games so this prerequisite cannot broaden bot behavior.
    if game_id != TEXAS_HOLDEM_PRACTICE_GAME:
        # Preserve the issue #189 scope boundary explicitly.
        raise ValidationError(f"Practice opponents are not configured for {game_id}")
    # Return the validated canonical game identifier.
    return game_id


# Return the three server-managed account snapshots without mutating balances.
def list_accounts(game_id: str = TEXAS_HOLDEM_PRACTICE_GAME) -> list[dict]:
    # Validate the requested allocation before reading player records.
    canonical_game = require_game(game_id)
    # Build one Admin-safe row for every fixed practice seat.
    rows = []
    # Preserve deterministic seat order across API, Admin, and future game wiring.
    for index, player_id in enumerate(PRACTICE_ACCOUNT_IDS, 1):
        # Validate that the configured id still resolves to an active bot account.
        account = practice_accounts.require_account(player_id)
        # Publish only controller and balance metadata already visible in Admin.
        rows.append({
            "seat_id": f"opponent_{index}",  # Preserve the held table's stable seat identity.
            "bot_id": player_id,  # Identify the controller in existing bot terminology.
            "player_id": player_id,  # Identify the real ledger-backed player wallet.
            "display_name": account.get("display_name", player_id),  # Publish the existing Admin-safe name.
            "balance": account.get("balance"),  # Show the current ledger-backed token balance.
            "status": account.get("status"),  # Expose whether the allocated account is active.
            "game_id": canonical_game,  # Bind the allocation to the held game proposal.
            "controller_policy": CONTROLLER_POLICY,  # Publish the deterministic action policy.
            "funding_amount": INITIAL_FUNDING,  # Document the fixed one-time seed amount.
        })
    # Return the complete fixed account allocation.
    return rows


# Seed every allocated account through one replay-safe ledger credit.
def fund_accounts(game_id: str = TEXAS_HOLDEM_PRACTICE_GAME) -> list[dict]:
    # Validate scope before the first ledger call.
    canonical_game = require_game(game_id)
    # Collect one funding result per deterministic practice seat.
    results = []
    # Fund all required accounts so the held table never uses virtual stakes.
    for account in list_accounts(canonical_game):
        # Construct one permanent per-game, per-account funding identity.
        action_key = f"practice:{canonical_game}:{account['player_id']}:funding-v1"
        # Credit the real bot wallet through the storage-enforced action primitive.
        result = practice_accounts.transact(account["player_id"], INITIAL_FUNDING, "PRACTICE_OPPONENT_FUNDED", action_key, canonical_game, None, "credit", "fund_account", component="initial_funding", details={"seat_id": account["seat_id"], "controller_policy": CONTROLLER_POLICY})
        # Publish the account identity with immutable ledger and replay evidence.
        results.append({"account": account, **result})
    # Return all three funding outcomes for Admin and tests.
    return results


# Execute one game-controller debit, refund, or payout against a real bot wallet.
def transact(player_id: str, amount, transaction_type: str, action_key: str, round_id: str, movement: str, controller_action: str, *, session_owner_id: str, component: str, details: dict | None = None, game_id: str = TEXAS_HOLDEM_PRACTICE_GAME) -> dict:
    # Validate the configured game before inspecting account membership.
    canonical_game = require_game(game_id)
    # Reject any bot id outside the three approved server-managed seats.
    if player_id not in PRACTICE_ACCOUNT_IDS:
        # Prevent a game controller from reaching unrelated bot wallets.
        raise ValidationError("Bot account is not allocated to this practice table")
    # Delegate the exact movement to the public core accounting seam.
    return practice_accounts.transact(player_id, amount, transaction_type, action_key, canonical_game, round_id, movement, controller_action, session_owner_id=session_owner_id, component=component, details=details)


# Return restart-safe append-only activity for Admin inspection.
def recent_activity(limit: int = 100, game_id: str = TEXAS_HOLDEM_PRACTICE_GAME) -> list[dict]:
    # Validate scope and delegate filtering to the core ledger-backed reader.
    return practice_accounts.recent_activity(limit, require_game(game_id))
