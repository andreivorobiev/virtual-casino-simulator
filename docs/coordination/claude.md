# Claude status

Written by Claude only. Codex reads this; do not edit it. Last updated 2026-08-07.

## Pull requests I authored (drafts; I never merge)

| PR | Branch | What it is | State |
|---|---|---|---|
| (opening) | `claude/account-admin-omnibus` | Account/enrollment/product-admin omnibus (#333, #334/#69, #335, #336, #351, #352, #349, #388, #378, #209) | **draft / WIP**, base `339de540f632c5b2897213b0223e4aa415171c9b`; #388 backend landed; remaining items in progress; not for merge until marked ready |
| #609 | `claude/607-viewport-containment-action-stability` | Issue #607 containment + action stability | merged |

## Active work — account/enrollment/product-admin omnibus (owner-directed 2026-08-07)

One draft PR per the owner packet. Base = exact protected main `339de54`. Constraints: `/api/v1` frozen; all new enrollment/provider behavior disabled by default; no live provider/mail/public/DNS/billing/production action; no touch to `casino/games/**`, `casino/core/ledger.py`, `casino/core/settlement.py`, paytables, deployment, PR #450. Fresh IDs only (TEST-159..168 reserved; main max TEST-157).

Ten items and current state:
1. #388 session-timeout policy — **backend landed** (enabled toggle, warning_minutes 0-10 <idle, updated_at/updated_by provenance, read-only session_status descriptor for registered+guest, Admin route actor stamp). UI + contract + tests + i18n pending.
2. #351 platform-owner RBAC lifecycle — pending (role_audit hash-chain core, grant/revoke, local-password step-up; provider step-up = recorded blocker).
3. #334/#69 account recovery — pending (wire existing password_reset service; disabled by default).
4. #333 enrollment readiness + Admin UI + provider kill switches — pending.
5. #335 disabled-by-default provider self-signup — pending (scaffolding-to-the-gate; shared identity gate NOT widened — deferred blocker).
6. #336 provider readiness/revocation/deletion evidence — pending (in-repo scaffolding + runbook + templates; console evidence = owner blocker).
7. #352 My Settings destination — pending (server foundation exists).
8. #349 feedback privacy/retention/deletion/export — pending (manual-only; publication adapter excluded — no owner approval).
9. #378 guest-trial conversion UI + admin-assisted — pending (API exists).
10. #209 read-only launch-readiness dashboard — pending.

## File claims / high collision risk

- Will touch: `casino/core/session_settings.py`, `casino/core/auth.py`, `casino/admin.py`, `casino/app.py`, `casino/wsgi.py` (allowlist blocks only, no gate widening), new `casino/core/role_audit.py`, `casino/core/oauth/**` (signup scaffolding), `web/admin.js`, `web/app.js`, `web/core/pwa.js`, `web/i18n/{en-US,ru-RU}/{shell,admin}.json`, `contracts/openapi/*.v2.yaml` + `contracts/compatibility/*`, `docs/requirements/requirements.json` (+ generated), `tests/**`, module descriptors + manifest, these coordination records.
- No touch: `casino/games/**`, `casino/core/ledger.py`, `casino/core/settlement.py`, paytables, deployment/release paths, `codex.md`.

## Questions / requests for Codex

- This is a WIP draft opened for visibility and pipeline entry per the owner packet; please do not integrate until it is marked ready-for-review with a green final head. I will run the full local matrix mirroring all nine workflow families before requesting review.

## Blockers I am waiting on (owner or Codex)

- Live enablement of any enrollment/provider/mail/public behavior: separate Workroom + #209 gate (out of scope for this PR).
- #336 provider-console/DNS/deletion evidence: provider console (owner).
- #335 shared-auth-gate widening: deferred follow-up under Workroom approval.
- #351 provider step-up semantics: recorded owner decision pending.
