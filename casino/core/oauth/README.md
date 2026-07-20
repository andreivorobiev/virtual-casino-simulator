# Invite-only OAuth runtime

This package implements issue #326 under `OAUTH-001` through `OAUTH-010`: Google and Facebook are integrated but independently disabled by default. Local-password login, recovery, manual invitation, and the no-public-signup boundary remain unchanged.

The runtime provides:

- exact v2 authorization-start and callback routes using authorization code, strict state, OIDC nonce for Google, and S256 PKCE for both providers;
- expiring one-time flow records atomically consumed before exchange and bound to provider, callback URI, browser owner, intended action, and the initiating user/session for linking;
- Google RS256 signature, issuer, audience/authorized-party, expiry, issued-at, nonce, and displayed-email verification;
- Facebook token validity, configured-app, expiry, data-access expiry, scope, and provider-subject/profile verification;
- durable JSON/MySQL-neutral links with transactional uniqueness for `(provider, subject)` and `(provider, Casino user)`;
- authenticated explicit first linking, prelinked-only subsequent sign-in, safe unlink, and provider-session rollback;
- secret-safe diagnostics, errors, redirects, rate limits, logs, cookies, and dependency-injected provider transports.

Provider email and profile fields are request-local display metadata. They never select, create, or link a Casino user. Persistent link rows contain only provider, opaque subject, canonical user id, and timestamps.

Run the listener-free suite with the configured Python runtime:

```powershell
python -m unittest discover -s tests/oauth -p "test_*.py" -v
```

Tests generate synthetic Google tokens at runtime, inject every Facebook/Google HTTP response, and need no real credentials or provider network access. Browser tests are mapped in the visual matrix; local Playwright execution is held by the owner's machine-performance instruction and belongs in GitHub checks.

Implementation does not authorize enablement. The exact Workroom approval gate in issue #326 is still required before a provider flag is enabled live, a security-sensitive enablement change is merged, or deployment occurs.
