# OAuth provider abstraction disabled foundation

This package is the provider-ready, disabled-until-configured foundation for GitHub issue #70. It maps to `OAUTH-001` through `OAUTH-005` and `USER-001`: local password login remains the only executable login flow, and every mocked external identity resolution points to an existing canonical user whose current record owns the player binding.

The package provides:

- static local, Google, and Facebook provider definitions;
- allowlisted Google and Facebook identity normalization from mocked claims;
- inert environment loading and secret-safe readiness diagnostics;
- exact callback URL, query, state, nonce, and PKCE S256 helpers based on issue #75;
- explicit one-to-one provider identity linking through an injected repository contract;
- one Admin-only, read-only diagnostic adapter at `GET /api/v2/admin/oauth/providers`;
- focused dependency-injected behavior with no HTTP client, provider SDK, provider action route, callback route, listener, or live browser flow.

Both external providers remain runtime-unavailable even when their exact enable flag is true and the client id, secret, and callback base are all present and valid. A `ready` diagnostic means only that inert configuration is structurally complete; it does not expose an authorization action, contact a provider, or claim live login works.

External identities never create users and never link by email. A first link requires the authenticated context's canonical user id; it must never accept a request-body target user. Persistence remains integration-owned. The repository contract accepts only provider, opaque subject, canonical user id, and timestamps, while tokens, codes, state, nonce, claims, email, display name, and avatar URL stay outside link records.

The login gate shows native-disabled Google and Facebook controls with localized explanation. Those controls contain no URL or click handler, while the local email/password form remains unchanged. Admin renders only allowlisted configuration and runtime facts; it never renders provider credentials, tokens, raw claims, or callback values.

Run the focused service-free tests from the repository root:

```powershell
python -m unittest discover -s tests/oauth -p "test_*.py" -v
```

No listener is required for the focused suite, and the tests inject in-memory configuration, users, and link storage. Central API/browser acceptance runs only in disposable copies on tracked loopback listeners.
