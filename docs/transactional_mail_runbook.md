# Transactional mail runbook

Requirements `MAIL-001` through `MAIL-006` define a disabled-by-default, provider-neutral boundary for future private invitation, email-verification, password-reset, and magic-link messages. Workroom issue #23 authorizes repository merge of the inert foundation and its secret-free Admin diagnostic only. It does not authorize live mail, provider or network access, provider-account changes, credentials, DNS or email-authentication changes, deployment, billing, signup, public exposure, or issue #209.

## Default and release boundary

The safe repository state is `CASINO_MAIL_ENABLED=false`, `CASINO_MAIL_NETWORK_ENABLED=false`, and `CASINO_MAIL_PROVIDER=disabled`. Provider access requires both switches, a supported adapter, one safe HTTPS canonical origin, a sender mailbox matching the separately verified sending domain, a unique mail digest key, and a provider credential. The Admin Operations card must report **Disabled** under repository defaults and **Release held** when configuration is complete but the independent network switch is false.

No application deployment may set either switch or supply a provider credential as an incidental configuration step. A live-release packet must identify the exact protected-main commit, deployment target, provider account, sender, domain, canonical origin, rollback owner, observation window, data-retention posture, and separately durable owner approval. It must also prove that public signup and unrestricted exposure remain unchanged.

## Sender and domain preparation

Before a separately approved live release, the operator must verify ownership of the exact sending domain in the selected provider account and record the provider's current DKIM result. SPF must authorize only the intended sender services and must not create a second SPF record. DMARC posture and reporting destinations require a distinct reviewed DNS change. Provider-account, DNS, SPF, DKIM, and DMARC work is never authorized by repository merge.

The configured `CASINO_MAIL_FROM_ADDRESS` mailbox domain must exactly match `CASINO_MAIL_SENDING_DOMAIN`. The canonical origin must be a single HTTPS origin with no path, query, fragment, alternate host, or redirect parameter. Templates own their fixed paths; callers cannot select a host or path.

## Domain or origin move

Treat any sender-domain, canonical-origin, or public-host move as a new release decision. Hold both mail switches, preserve the existing delivery state, and revalidate:

1. canonical HTTPS origin and certificate posture;
2. fixed invitation, verification, reset, and magic-link paths;
3. OAuth callback origins and provider-console registrations, without changing them unless separately approved;
4. sender mailbox alignment, provider domain verification, DKIM, SPF, and DMARC;
5. EN/RU plain-text and semantic HTML rendering;
6. recipient suppression, retry-wait, uncertain, and retention state;
7. rollback to the prior disabled configuration.

Do not reuse an approval tied to the old host, domain, sender, provider account, or protected-main SHA.

## Bounded release smoke

A separately approved live smoke uses an owner-designated non-user recipient and one purpose-bound test token. Record only the opaque delivery identifier, exact release SHA, purpose, terminal status, and timestamps. Never place the address, bearer, tokened URL, provider credential, or raw provider response in logs, comments, screenshots, or evidence. Verify one delivery for a replayed caller idempotency key, the Admin aggregate transition, and that no consumer route or public-signup surface was introduced.

Timeouts and other ambiguous provider outcomes become **Needs reconciliation** and must not be automatically retried. Confirm provider acceptance by authorized provider-side evidence before any manual resolution. Known non-accepted transient failures may follow the bounded retry schedule; exhausted attempts are terminal.

## Bounce, complaint, and suppression handling

This foundation exposes no public provider webhook. A future verified provider event consumer requires a separate contract and approval. Internal suppression accepts only fixed bounce, complaint, or invalid-recipient categories and persists a keyed recipient digest. Admin diagnostics show aggregate counts only. Never copy raw event bodies or recipient identifiers into application state or acceptance evidence.

## Rollback and recovery

Rollback first sets both mail switches false and verifies **Disabled** in the Admin card. It does not delete delivery or suppression state, rotate credentials, edit provider accounts, or change DNS. Structurally malformed state is preserved unchanged for operator recovery; do not replace it with an empty outbox. Recover from a verified copy, validate the schema and keyed-only fields offline, and keep provider delivery held until reconciliation is complete.

After the configured retention period, only terminal delivery and suppression metadata is eligible for bounded cleanup. Active sending, retry-wait, and uncertain records must not be discarded to manufacture a clean status.
