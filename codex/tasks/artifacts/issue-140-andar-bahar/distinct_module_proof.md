# Issue #140 Distinct Module Proof

Decision: accepted as a distinct catalog module through issue #77 integration.

Evidence:

- Andar Bahar has a unique rule nucleus: one exposed joker/match card, alternating Andar/Bahar reveal order, and first same-rank match deciding the winning side.
- Existing registered or draft card games in this repo do not implement that nucleus:
  - Baccarat resolves hand totals with Punto Banco drawing rules.
  - Hi-Lo resolves a higher/lower comparison against a visible card.
  - Dragon Tiger and Casino War resolve direct high-card comparisons.
  - Red Dog resolves spread-based odds between two cards.
- The implementation uses shared card primitives from `casino.core.cards`, but imports no existing game module.
- The canonical descriptor at `modules/andar_bahar.json` owns catalog registration, route metadata, compatibility, and discovered test evidence.

Countability: distinct and countable with permanent requirements `AB-001` through `AB-005` and catalog sort order `250`.
