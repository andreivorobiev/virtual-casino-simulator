# Disabled-by-default invite-only OAuth integration for #326

The earlier disabled foundation remains the base for the Workroom #25-approved repository runtime. The shared app, auth contract, login/current-account/Admin presentation, requirement registry, visual matrix, test discovery, module descriptors, and manifest now describe the disabled-by-default existing-account flow without authorizing live provider access.

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
- `CASINO_OAUTH_NETWORK_RELEASED_GOOGLE`
- `CASINO_OAUTH_NETWORK_RELEASED_FACEBOOK`
- `CASINO_OAUTH_DIGEST_KEY`

Diagnostics expose only presence booleans, status, callback URL, release-latch state, missing setting names, and stable problem codes. Adapters must not log or serialize configuration objects, raw claims, authorization codes, access or refresh tokens, state, nonce, or PKCE material.

## Integrated disabled surface

- `GET /api/v2/auth/oauth/providers` exposes boolean availability only.
- `POST /api/v2/auth/oauth/{google|facebook}/start` and the matching `GET` callback exist only for the exact reviewed providers.
- `GET /api/v2/me/oauth/providers` and `POST /api/v2/me/oauth/{google|facebook}/unlink` expose boolean current-account link state without provider identity data.
- `GET /api/v2/admin/oauth/providers` remains read-only, repeats the Admin role check, and exposes only allowlisted diagnostics.
- Login and current-account controls remain native-disabled unless the applicable provider flag, structurally valid configuration, and independent network-release latch are all true.
- Admin renders provider configuration status separately from Operations health; OAuth diagnostic failure cannot change `/healthz`, `/readyz`, or `/api/v2/admin/operations` state.
- Permanent `OAUTH-001` through `OAUTH-010`, `TEST-045`, and `TEST-093` trace configuration, callbacks, mocked claims, identity-link rules, persistence, disabled UI, and focused acceptance.
- Google and Facebook keep `runtime_available=false` unless both independent gates are true; both gates default false.

The registered routes never create or merge accounts and never link by email. A link start requires the authenticated canonical user, a local-password session, explicit confirmation, CSRF proof, and exact browser/session binding. Callback metadata stores only HMAC proofs, while nonce and PKCE material live in a separate document and survive a recoverable provider-availability failure. Provider transport is unreachable while the independent release latch is false.

## Implemented repository safeguards

A disabled flow now:

1. Sanitizes access and request logs so callback queries, codes, state, and unexpected exception text never enter logs or payloads.
2. Preserves duplicate query parameters so callback validation rejects ambiguity before exchange.
3. Uses atomic JSON/MySQL mutations for flow claims, link uniqueness, replay protection, and durable rate limits.
4. Preserves malformed storage for recovery instead of replacing it with an empty container.
5. Verifies provider signature/issuer/audience/expiry and applicable nonce/PKCE rules before accepting an opaque provider subject.
6. Revokes provider-authenticated sessions when a link is removed or its provider gate closes.

## Live-enable blockers

Real provider login remains blocked on separate provider-account, credential, callback-console, network-release, security/privacy/data-deletion, rollback, deployment, and owner release approval. A `configuration_ready` diagnostic, repository merge, or deployment cannot bypass those gates. No live enablement, public signup, account creation, DNS change, or unrestricted exposure is authorized by this package.
