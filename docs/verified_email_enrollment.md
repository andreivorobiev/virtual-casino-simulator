# Verified-email enrollment

Requirements: `AUTH-018`, `USER-010`, and `TEST-171`.

First-party email signup is a disabled-by-default, recoverable pending-enrollment saga. The existing `/api/v1` contract is unchanged. The additive `/api/v2/auth/signup` route now creates only a pending credential verifier and sends a purpose-bound `email_verification` token through the existing transactional-mail boundary. Before verification there is no canonical user, player, balance, ledger event, or session.

## Activation order

1. The service claims the pending row under a caller idempotency key and reserves canonical mailbox uniqueness.
2. The current recipient-bound token generation is consumed exactly once.
3. A deterministic inactive local user and zero-balance inactive player are provisioned.
4. `casino/core/ledger.py::credit_once` applies the configured `CASINO_ACCOUNT_STARTING_BALANCE` under `email-enrollment:<enrollment-id>:starting-balance`.
5. The funded player and then the user become active. Verification never creates a session; the user must sign in explicitly.

The token-consumed phase is durable. If the process stops after user creation, wallet creation, ledger credit, or player activation, the same caller key resumes the existing identifiers and the ledger action replays without a second credit. A changed key cannot take over post-consumption work.

## Public lifecycle

- `POST /api/v2/auth/signup` begins pending enrollment.
- `POST /api/v2/auth/signup/resend` prepares a non-consumable candidate, preserves the prior bearer through provider delivery, and atomically promotes the candidate only after a `sent` receipt.
- `POST /api/v2/auth/signup/verify` consumes the current bearer and completes recoverable activation.
- `POST /api/v2/auth/signup/cancel` requires the current delivered bearer, then revokes pending work before verification without consuming the later verify action.

Initiation and resend use the same generic pending acknowledgement. Verification failures are generic across malformed, expired, consumed, cancelled, mismatched, unavailable, and raced requests. Cancellation rejects absent, malformed, stale, candidate, cross-recipient, rate-limited, and raced ownership through one generic error; the exact completed cancellation key replays its terminal receipt after token revocation.

## Release and privacy boundaries

`CASINO_SIGNUP_ENABLED` remains false by default. Transactional mail still requires its independent feature, network, provider, sender, origin, credential, and digest-key readiness gates. This change does not enable public signup, live mail, OAuth, DNS, or production provider traffic.

Raw verification bearers are never persisted in pending, token-delivery, audit, browser session-storage, or URL history. Pending state retains the normalized recipient needed for delivery, a one-way lookup digest, a password verifier rather than a raw password, fixed lifecycle metadata, and opaque identifiers. Browser links scrub the bearer into module-only memory on arrival. Verify and cancel controls remain disabled before that link arrives; their independent random replay keys are stored under bearer-digest-derived session keys, retained only across ambiguous failure, and removed after acknowledged terminal success.

Completion and cancellation remove the normalized recipient, password verifier, display name, locale, and terms value in the same terminal pending-row commit. Only keyed replay digests, fixed lifecycle state, and opaque audit identifiers remain, so exact lost-response replay does not require terminal credential or profile retention.

Initiate, resend, verify, and cancel have independent durable per-client rate windows. Exact caller-idempotent replays are classified before charging, while a different request consumes allowance. Recipient resend cooldown and mail-provider suppression/rate/uncertain results return the same generic acknowledgement as an absent recipient and never invalidate the last usable bearer. Cancellation charges malformed, wrong, stale, absent, and cross-recipient distinct attempts before bearer classification, then rechecks the exact current token and delivery generation during terminalization so a concurrent resend cannot let predecessor A cancel replacement B.

Delivery persists one bounded replacement subrecord with generation, predecessor, candidate, and provider-receipt phases. A crashed worker is reconciled before later initiate, resend, verify, or cancel decisions: stale pre-provider candidates are discarded after the ambiguity window; provider-confirmed candidates promote idempotently; cancellation removes the recovery packet and revokes every current or candidate bearer before a stale callback can resume it.

Scrubbed `complete` and `cancelled` replay metadata is retained for 30 days by default. Every enrollment mutation prunes expired terminal rows inside the provider transaction while preserving pending, delivering, verifying, malformed, and recent terminal state for explicit recovery.
