# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered long-suite driver for Scratch Cards after #77 integration."""

# Exercise one complete card through only public session-bound actions.
def play(client, index):
    # Build stable unique purchase and reveal identities for this long-suite iteration.
    start_id = f"long-scratch-start-{index}"
    # Build a separate retry-safe identity for the complete reveal action.
    reveal_id = f"long-scratch-reveal-{index}"
    # Start one ledger-backed card through the additive public action.
    started = client.call("/api/v1/games/scratch-cards/cards", "POST", {"client_request_id": start_id, "wager": 1})
    # Read the stable player-scoped card identity from the masked response.
    card_id = started["card"]["card_id"]
    # Verify every new card begins with all private prizes covered.
    assert all("prize" not in cell for cell in started["card"]["cells"]), "Scratch Card start leaked a covered prize"
    # Reveal every position through one public action so any outcome reaches settlement.
    settled = client.call(f"/api/v1/games/scratch-cards/cards/{card_id}/scratches", "POST", {"action_id": reveal_id, "positions": list(range(9))})
    # Verify the real backend returned one terminal card with every prize public.
    assert settled["card"]["status"] == "settled", "Scratch Card did not settle after all positions"
    # Verify exactly nine authorized prizes are present after settlement.
    assert sum("prize" in cell for cell in settled["card"]["cells"]) == 9, "Scratch Card terminal response omitted prizes"
    # Retry the same reveal identity through the real backend.
    replay = client.call(f"/api/v1/games/scratch-cards/cards/{card_id}/scratches", "POST", {"action_id": reveal_id, "positions": list(range(9))})
    # Verify exactly-once action recovery is explicit.
    assert replay["replayed"] is True, "Scratch Card retry was not reported as replayed"
    # Verify the stable card identity survives the retry.
    assert replay["card"]["card_id"] == card_id, "Scratch Card retry changed card identity"
