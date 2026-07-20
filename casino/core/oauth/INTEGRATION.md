# Invite-only OAuth integration for issue #326

## Exact configuration contract

- `CASINO_GOOGLE_CLIENT_ID`
- `CASINO_GOOGLE_CLIENT_SECRET`
- `CASINO_FACEBOOK_APP_ID`
- `CASINO_FACEBOOK_APP_SECRET`
- `CASINO_OAUTH_PUBLIC_BASE_URL`
- `CASINO_OAUTH_ENABLED_GOOGLE`
- `CASINO_OAUTH_ENABLED_FACEBOOK`

Each provider remains unavailable unless its own enable flag is explicitly true, both of its credential variables are non-empty, and the shared base produces an accepted exact callback. Credentials and provider responses must remain in the deployment secret store, never source, fixtures, logs, issue text, PR text, screenshots, or evidence.

## Exact callbacks

- `http://localhost:8765/api/v2/auth/oauth/google/callback`
- `http://localhost:8765/api/v2/auth/oauth/facebook/callback`
- equivalent fixed development copies on ports `8766` and `8767`;
- `https://<owned-public-hostname>/api/v2/auth/oauth/google/callback`;
- `https://<owned-public-hostname>/api/v2/auth/oauth/facebook/callback`.

Do not substitute an IP literal, wildcard, trailing slash, alternate port, query, fragment, or base path. Register only the callback that matches `CASINO_OAUTH_PUBLIC_BASE_URL` for that deployment.

## Account and storage boundary

Public signup and provider-driven user creation do not exist. Linking starts only from an active authenticated local-password account after an explicit checkbox confirmation. The flow retains the exact user and session; callbacks cannot submit a target. Provider email is never passed to `find_user_by_email`.

Sign-in resolves only `(provider, subject)` to an existing link and then rechecks the canonical user's active state and player binding. Unlink requires a retained local password, removes only the authenticated user's provider row, and revokes only sessions created through that provider.

Flow and link updates use `StorageProvider.update_document`. JSON holds a thread and operating-system document lock across read/mutate/atomic replace. MySQL holds a transaction and `SELECT ... FOR UPDATE`. No provider token, code, state, nonce, verifier, credential, email, profile, or raw response is stored in identity-link persistence.

## Provider console inputs still required

The owner must create or select the two provider applications, supply the public client/app identifiers and confidential secrets through deployment secret storage, register the exact callbacks, configure the approved scopes, complete provider privacy/data-deletion settings, and validate current provider-console behavior against the pinned integration before any enable flag changes.

## Workroom gate

The following exact approval must be durably recorded in a separate Workroom issue before live enablement, merge of a security-sensitive enablement change, or deployment:

> APPROVE: Enable Google and Facebook authentication only for existing private-invite Casino accounts. Keep public signup disabled, require authenticated explicit linking, never link by email, and keep each provider disabled until its console configuration, credentials, callbacks, security checks, rollback, and owner release approval are complete.

Issue #326, this disabled implementation, tests, or a draft PR do not satisfy that separate approval gate.
