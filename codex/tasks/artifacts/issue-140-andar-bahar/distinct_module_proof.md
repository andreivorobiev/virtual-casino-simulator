# Issue #140 Distinct Module Proof

Decision: promote to isolated draft implementation slice.

Evidence:

- Andar Bahar has a unique rule nucleus: one exposed joker/match card, alternating Andar/Bahar reveal order, and first same-rank match deciding the winning side.
- Existing registered or draft card games in this repo do not implement that nucleus:
  - Baccarat resolves hand totals with Punto Banco drawing rules.
  - Hi-Lo resolves a higher/lower comparison against a visible card.
  - Dragon Tiger and Casino War resolve direct high-card comparisons.
  - Red Dog resolves spread-based odds between two cards.
- The implementation uses shared card primitives from `casino.core.cards`, but imports no existing game module.
- The descriptor is parked as proposal-only and does not claim catalog count acceptance until #77 integrates shared files.

Countability: distinct and countable pending #77 shared catalog/router/manifest/requirements/visual-matrix/test-discovery integration.
