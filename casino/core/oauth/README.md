# Disabled-by-default invite-only OAuth runtime

This package implements the disabled-by-default Google and Facebook runtime for GitHub issue #326. It maps to `OAUTH-001` through `OAUTH-010`, `TEST-093`, and `USER-001`. Local password login remains available, and an external identity can authenticate only after an existing active private-invite account explicitly links that provider while authenticated.

The package provides:

- static local, Google, and Facebook provider definitions;
- allowlisted Google and Facebook identity normalization from mocked claims;
- secret-safe readiness diagnostics plus an independent false-by-default provider-network release latch;
- exact callback URL, query, state, nonce, and PKCE S256 helpers based on issue #75;
- explicit one-to-one provider identity linking through atomic JSON/MySQL persistence;
- separate HMAC-only flow metadata and nonce/PKCE proof storage with recoverable exchange leases;
- exact additive v2 status, start, callback, current-account link, unlink, and Admin diagnostic routes;
- dependency-injected provider adapters and transport ports that remain unreachable unless both the provider flag and independent network-release latch are true.

Both external providers remain runtime-unavailable by default. Structurally valid configuration is insufficient: each provider also requires its exact enable flag and its independent network-release latch. Repository merge, deployment, or a `ready` diagnostic does not authorize network contact or live provider enablement.

External identities never create users, merge users, or link by email. A first link requires an authenticated local-password session for the canonical existing user, explicit confirmation, and exact browser/session/CSRF binding. Link persistence accepts only provider, opaque subject, canonical user id, and timestamps; tokens, codes, state, nonce, claims, email, display name, and avatar URL stay outside link records.

The login and current-account controls expose only boolean availability/link state and remain disabled when the release latch is closed. Admin renders only allowlisted configuration and runtime facts; it never renders provider credentials, tokens, raw claims, authorization URLs, or callback query values.

Run the focused service-free tests from the repository root:

```powershell
python -m unittest discover -s tests/oauth -p "test_*.py" -v
```

No listener or provider network is required for the focused suite. Central API/browser acceptance uses disposable loopback copies and mocked provider responses; live provider, console, credential, DNS, deployment, and public-signup work remain separately prohibited.
