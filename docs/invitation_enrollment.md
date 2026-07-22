# Private invitation enrollment runbook

This runbook governs the disabled-by-default Admin invitation and private redemption code approved in Workroom #24. Repository merge does not authorize live enrollment, mail delivery, provider or network access, credentials, DNS, deployment, public signup, or unrestricted exposure.

## Authority and default state

- `CASINO_INVITATIONS_ENABLED` controls Admin issuance and defaults to false.
- `CASINO_ENROLLMENT_ENABLED` controls public redemption and defaults to false.
- Transactional mail remains separately controlled by its feature and provider-network release gates. Invitation issuance requires mail readiness `ready` before a bearer is created.
- The public `/api/v2/auth/redeem-invitation` route is present for the approved private flow, but returns one generic error while redemption is disabled.
- `/api/v1` remains frozen and exposes no invitation route.

No flag may be changed merely because this code is merged. Live use requires a separately recorded release decision, a named restricted-preview recipient policy, current immutable release evidence, rollback ownership, and verification of every mail/provider security gate.

## Lifecycle

1. An authenticated Admin supplies an approved mailbox, one governed locale, and a caller idempotency key.
2. The service reserves an account-free invitation row under the JSON/MySQL document lock, applies actor and keyed-recipient rate limits, and mints a purpose-bound `invitation` token.
3. The bearer exists only in transient memory and the approved bilingual mail payload. Durable token and mail state contain keyed digests and opaque identifiers, not the bearer or tokened URL.
4. A resend revokes the prior generation and observes the fixed cooldown. Revocation commits the invitation terminal state before revoking the token.
5. Redemption requires the invited mailbox, canonical strong password policy, a supported locale, explicit acceptance of the exact current terms version, and a caller idempotency key.
6. The recovery saga reserves mailbox uniqueness, consumes or idempotently replays the token, records the token-consumed phase, creates an inactive deterministic local identity, ensures one ledger-backed player wallet, activates the identity with recorded terms, and finalizes the invitation.
7. An interruption before token consumption releases the account-free reservation and returns the invitation to pending. An interruption after consumption preserves the exact recovery claim; only the same caller binding may resume it.

## Privacy and audit

- Admin APIs and UI return only a masked recipient hint. Raw recipient values must not appear in logs, screenshots, evidence sidecars, audit events, or public responses.
- Public disabled, malformed, expired, revoked, replayed, raced, and policy-rejected requests all return `invitation_unavailable`.
- Passwords are validated transiently and stored only through the canonical password hash boundary.
- Caller keys and recipient lookup values are stored only as domain-separated keyed digests.
- Audit history accepts only opaque actor/invitation identifiers, fixed reasons, lifecycle states, and timestamps.
- Invitations remain local identities and never create or infer Google/Facebook links.

## Abuse, retention, and recovery

- Admin issuance and keyed-recipient delivery counts use fixed rolling-window ceilings.
- Resend has a fixed cooldown and every generation replaces the prior token.
- Lifecycle history is bounded. Terminal redeemed/revoked metadata is removed only after the configured full retention period.
- Malformed invitation, token, mail, user, or player state is preserved unchanged for operator recovery. Do not normalize, replace, or delete malformed documents automatically.
- A `redeeming` row in phase `claimed` may be taken over only after the configured claim timeout and only before token consumption. Post-consumption recovery always requires the original caller binding.

## JSON and MySQL checks

Before any separately authorized live release:

1. Confirm exact-head `API-INVITE-001`, `API-INVITE-002`, and `BR-INVITE-001` pass.
2. Confirm disposable MySQL `STORAGE-MYSQL-LIVE-001` races independent processes through claim, token consume, account, player wallet, activation, and finalization, producing exactly one active account and wallet.
3. Confirm JSON cross-process evidence reaches one terminal invitation with one account and wallet.
4. Confirm the v2 contract digest, module versions, requirements, and generated docs match the deployed immutable release.
5. Confirm EN/RU evidence for Admin disabled/release-held/empty/pending/redeemed/error states and public form/terms/error/success/focus/reduced-motion/zoom states at all four governed viewports contains no raw mailbox, bearer, URL, or credential.

## Release and rollback

Live release requires all four invitation/mail gates, exact canonical Origin and CSRF policy, provider readiness, and a separately approved recipient cohort. Begin with a single private recipient and observe only masked lifecycle state and aggregate mail diagnostics.

Rollback by disabling redemption first, then invitation issuance. This prevents new claims and new mail while retaining recovery state. Disable mail network release separately when delivery must stop. Do not delete pending or `redeeming` rows during rollback; preserve them for exact-key recovery or Admin revocation after review.

If any account, wallet, token, or invitation invariant is uncertain, hold the flow disabled, preserve state and artifacts, and escalate for operator reconciliation. Never repair uncertainty by minting a second account, reusing a consumed bearer with changed inputs, or broadening public access.
