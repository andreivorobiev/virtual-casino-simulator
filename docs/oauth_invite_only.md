# Invite-only OAuth operations boundary

Requirements: OAUTH-007, OAUTH-008, OAUTH-009, OAUTH-010, AUTH-007, and TEST-093.

This repository contains a disabled-by-default Google and Facebook OAuth implementation for existing active private-invite accounts. It does not provide public signup, create accounts, merge accounts, select accounts by provider email, or replace local-password recovery.

## Repository defaults

Each provider has two independent false-by-default gates:

- configuration request: `CASINO_OAUTH_ENABLED_GOOGLE` or `CASINO_OAUTH_ENABLED_FACEBOOK`;
- provider-network release: `CASINO_OAUTH_NETWORK_RELEASED_GOOGLE` or `CASINO_OAUTH_NETWORK_RELEASED_FACEBOOK`.

Runtime availability requires both gates, complete credentials, a valid canonical public base URL, and a strong `CASINO_OAUTH_DIGEST_KEY`. Configuration readiness alone never constructs a provider adapter or authorizes network access. Workroom #25 comment 5027642551 authorizes the disabled repository implementation only.

## Account and identity boundary

The first link requires the exact authenticated active private-invite local-password user, the exact initiating session, browser binding, CSRF proof, and explicit confirmation. Later provider sign-in resolves only an existing unique `(provider, subject)` link. Provider email and display claims are never account selectors. Guests, disabled users, provider-only identities, and accounts without local-password recovery cannot link.

Unlink removes only the current user's selected provider link and revokes sessions authenticated by that provider. Local-password sessions and recovery remain available.

## Flow persistence and recovery

Flow metadata stores HMAC verifiers for state, callback URI, browser owner, optional link user/session owner, and exchange-claim ownership. Nonce and PKCE verifier live in a physically separate proof document keyed only by an internal flow id. Raw state, callback URI, browser proof, user id, and session id never share a durable record with nonce or PKCE material.

A callback atomically leases one flow. A fixed transient provider-unavailable result releases the exact lease back to pending until its original expiry. Cryptographic, issuer, audience, app-binding, identity, replay, and post-exchange authorization failures are terminal and leave a replay tombstone. Durable rate buckets and identity-link uniqueness use the same JSON/MySQL atomic document transaction boundary.

Malformed OAuth documents are operator-recovery state. The application copies corrupt JSON evidence where applicable and aborts mutation; it must not replace malformed state with an empty default. For MySQL, preserve the affected `casino_documents` row before any reviewed repair.

## Privacy and audit

Application logs use only fixed event names plus bounded provider, action, boolean, or count fields. Never log or retain authorization URLs, codes, state, nonce, PKCE verifier, access or ID tokens, provider secrets, callback query strings, raw browser/session proofs, provider responses, recipient addresses, or provider subjects in browser evidence.

Identity links retain only provider, provider subject, canonical user id, and bounded timestamps. Account and public status APIs return provider identifiers and booleans only. Admin diagnostics return allowlisted readiness facts and setting names, never values.

Provider data-deletion and privacy obligations must be reviewed in each provider console before any future live release. A future provider removal must revoke its Casino sessions, remove approved identity links under retention policy, disable both gates, and preserve privacy-safe audit history.

## Future live-release checklist

Repository merge, deployment, configured credentials, or green checks do not authorize live provider access. A separate owner-approved release must verify, per provider:

1. provider account and application ownership;
2. exact production callback registration and canonical-origin alignment;
3. secret delivery and rotation without repository or log exposure;
4. scopes, consent, privacy notice, data deletion, and retention;
5. provider-specific signature/app-binding, issuer, audience, nonce, expiry, and error behavior;
6. rate-limit, transient ambiguity, rollback, unlink, and provider-session revocation evidence;
7. monitoring and bounded smoke evidence without raw identity material;
8. explicit owner authorization to set that provider's network-release latch true.

No live release may authorize public signup, provider-created accounts, email linking, DNS or firewall changes, billing, deployment, or unrestricted launch #209 unless those actions receive their own explicit authority.

## Rollback

Set the affected provider-network release latch false first. This blocks new starts, callbacks, adapter construction, and continued authorization of provider-authenticated sessions while preserving local-password access. If required, also set the provider enable flag false, revoke provider-authenticated sessions, and unlink only reviewed affected bindings. Do not delete malformed or disputed persistence; preserve it for operator recovery and audit.

Re-enablement requires a new exact readiness and security review. Never infer release authority from a prior repository merge or stale provider configuration.
