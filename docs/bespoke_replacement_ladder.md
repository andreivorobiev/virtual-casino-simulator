# Bespoke infrastructure replacement ladder

This is a decision record, not an implementation task. It ranks which bespoke
infrastructure layers should be replaced by mature third-party dependencies
*if and when each next breaks*, so that the next P1 in a bespoke layer triggers
a deliberate replace-versus-patch decision from this ladder instead of another
patch by default.

## Why this record exists

HTTP serving, routing, authentication, sessions, CSRF, transactional mail,
OAuth, and connection pooling are all hand-rolled. The implementations are
careful and consistent, but the maintenance surface is large for one owner plus
agents, and the open and recently-closed P1s cluster in the bespoke auth and
session layer — which is direct evidence about where bespoke is costing the
most. This ladder makes the replace-versus-patch choice explicit and evidence-
driven rather than implicit.

## The ladder (replace first at the top)

| Rank | Bespoke layer | Current evidence | Disposition on next break |
| --- | --- | --- | --- |
| 1 | Session storage (first-class keyed JSON and MySQL rows after #1039) | Session-architecture epic, prior P1 symptoms, and provider-parity concurrency evidence | **Monitor the replacement** — do not reintroduce an aggregate session document; continue the broader session-redesign epic. |
| 2 | Serving stack (stdlib `ThreadingHTTPServer` plus a parallel gunicorn WSGI path) and the MySQL connection pool (default 2, cap 16) | Concurrency-ceiling qualification finding | **Replace / harden** — standardize on the WSGI path; size and instrument the pool. |
| 3 | Auth / CSRF / one-time tokens | P1s cluster here | Prefer a mature framework primitive at the next material break; migrate behind the existing provider/service seams. |
| 4 | Transactional mail and OAuth adapters | Disabled by default; bespoke but bounded | Adopt a maintained provider SDK when live enablement is actually scheduled, not before. |
| 5 | Routing | Small, stable | Patch; revisit only if it starts gating features. |

## Explicitly keep-bespoke (the differentiated core)

- **Money and the ledger** — exactly-once settlement, entropy-committed
  outcomes, and the wallet contract are the differentiated core.
- **Game logic and engines** — the 46-game catalog and its server-authoritative
  outcomes are the product.

These are deliberately *not* replacement candidates: replacing them would trade
away the parts that make this repository what it is, and they are not where the
P1 evidence clusters.

## How to use this record

When the next P1 lands in a bespoke layer, read this ladder before writing a
patch. If the layer is ranked for replacement and this is its next material
break, open (or advance) the replacement lane and justify the decision here
rather than patching by default. Update the evidence column as P1s are opened
and closed so the ranking stays honest.

## Linked work

- [Session storage redesign epic (#1041)](https://github.com/andreivorobiev/virtual-casino-simulator/issues/1041)
  and its [per-session-storage issue (#1039)](https://github.com/andreivorobiev/virtual-casino-simulator/issues/1039)
  — #1039 implements the per-session storage replacement; the epic retains broader session-architecture follow-up.
- [Concurrency-ceiling finding (#1040)](https://github.com/andreivorobiev/virtual-casino-simulator/issues/1040)
  — serving stack and pool sizing.
