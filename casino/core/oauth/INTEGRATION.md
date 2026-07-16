# OAuth disabled-foundation integration for #70

GitHub issue #77 released this branch to integrate only the owner-approved disabled foundation. The shared app, auth contract, login/Admin presentation, requirement registry, visual matrix, test discovery, module descriptors, and manifest now describe the inert provider abstraction without enabling a provider action.

## Exact callback reservation

The integration owner must preserve the issue #75 paths exactly:

- `http://localhost:8765/api/v2/auth/oauth/google/callback`
- `http://localhost:8765/api/v2/auth/oauth/facebook/callback`
- equivalent fixed local copies on ports `8766` and `8767`;
- `https://<owned-public-hostname>/api/v2/auth/oauth/google/callback`;
- `https://<owned-public-hostname>/api/v2/auth/oauth/facebook/callback`.

Do not substitute `127.0.0.1`, add a trailing slash, add a base path, use a wildcard, or expose a callback before the deployment gates are approved. The helper accepts HTTP only for the three reserved `localhost` origins and HTTPS only for a DNS hostname using the default port.

## Configuration contract

The isolated diagnostics consume the exact issue #75 names:

- `CASINO_GOOGLE_CLIENT_ID`
- `CASINO_GOOGLE_CLIENT_SECRET`
- `CASINO_FACEBOOK_APP_ID`
- `CASINO_FACEBOOK_APP_SECRET`
- `CASINO_OAUTH_PUBLIC_BASE_URL`
- `CASINO_OAUTH_ENABLED_GOOGLE`
- `CASINO_OAUTH_ENABLED_FACEBOOK`

Diagnostics expose only presence booleans, status, callback URL, missing setting names, and stable problem codes. Live adapters must not log or serialize configuration objects, raw claims, authorization codes, access or refresh tokens, state, or nonce.

## Integrated disabled surface

- `GET /api/v2/admin/oauth/providers` is read-only, uses the standard envelope, repeats the Admin role check at the route boundary, and exposes only allowlisted diagnostics.
- The login gate renders Google and Facebook as native-disabled controls with no URL or event handler and explains the hold in English and Russian.
- Admin renders provider configuration status separately from Operations health; OAuth diagnostic failure cannot change `/healthz`, `/readyz`, or `/api/v2/admin/operations` state.
- Permanent `OAUTH-001` through `OAUTH-006` and `TEST-045` trace configuration, callbacks, mocked claims, identity-link rules, disabled UI, and focused acceptance.
- Google and Facebook keep `runtime_available=false` even if inert environment configuration is structurally ready.

No start, link, callback, exchange, provider SDK, or live transport route is registered. The callback helpers remain pure and service-free. Identity linking remains injected and non-persistent; no user is created and no email-based association occurs.

## Deferred runtime work

A later explicitly authorized auth/storage owner must first:

1. Harden request logging and unexpected-error handling so authorization codes, state, and other callback query data can never enter logs or error payloads.
2. Preserve duplicate query parameters through routing so the callback validator can reject ambiguity before any exchange.
3. Persist state, nonce, and PKCE verifier as atomic one-time flow records and reject replay, expiry, provider, callback, and session-owner drift.
4. Add a dedicated allowlisted identity-link store with atomic uniqueness for `(provider, subject)` and `(provider, user_id)` across every supported storage process.
5. Implement provider adapters that verify signatures, issuer, audience, expiry, nonce, and applicable PKCE before returning an allowlisted identity.
6. Add authorization-start, link, and callback contracts/routes only after a separate owner approval releases live runtime work.

## Live-enable blockers

Real provider login remains blocked on user-created provider applications and credentials, exact provider-console callback registration, successful real callback testing, an approved owned HTTPS hostname, secure-cookie/deployment hardening under #71, and public privacy, terms, and data-deletion pages. A `configuration_ready` diagnostic cannot bypass any provider-console, callback-test, secure-cookie, legal, or #71 deployment gate. No live enablement or public exposure is authorized by this package.
