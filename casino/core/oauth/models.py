# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Secret-safe identity-provider models and injectable OAuth ports.

Requirements: OAUTH-001, OAUTH-004, OAUTH-005, and USER-001.
"""

# Import dataclass support so immutable provider records stay explicit and testable.
from dataclasses import dataclass, field
# Import mapping and protocol types so provider implementations can remain dependency-injected.
from typing import Mapping, Protocol


# Describe one local or external identity provider without embedding credentials or live SDKs.
@dataclass(frozen=True)
class ProviderSpec:  # Keep provider metadata immutable and credential-free.
    # Store the stable lower-case provider identifier used in paths and persisted links.
    provider_id: str
    # Store the provider flow class so local password login remains distinct from OAuth.
    flow: str
    # Store only the minimum provider scopes approved by issue #75.
    scopes: tuple[str, ...] = field(default_factory=tuple)
    # Store whether the provider is available without external configuration.
    enabled_by_default: bool = False
    # Name the optional environment flag that requests external-provider enablement.
    enabled_env: str | None = None
    # Name the optional public client-id environment setting without storing its value.
    client_id_env: str | None = None
    # Name the optional secret environment setting without storing its value.
    client_secret_env: str | None = None


# Represent the allowlisted identity fields produced from mocked or future provider claims.
@dataclass(frozen=True)
class VerifiedIdentity:  # Keep only allowlisted provider identity fields.
    # Store the stable provider identifier needed for compound uniqueness checks.
    provider: str
    # Store the provider-owned opaque subject without exposing it through object representations.
    subject: str = field(repr=False)
    # Store an optional normalized email without exposing personal data through representations.
    email: str | None = field(default=None, repr=False)
    # Record whether the provider supplied an explicit verified-email assertion.
    email_verified: bool = False
    # Store an optional display name without exposing personal data through representations.
    display_name: str | None = field(default=None, repr=False)
    # Store an optional HTTPS avatar URL without exposing it through representations.
    avatar_url: str | None = field(default=None, repr=False)

    # Return non-sensitive facts suitable for Admin or Operations diagnostics.
    def diagnostic(self) -> dict:
        # Publish presence booleans instead of provider claim values.
        return {"provider": self.provider, "subject_present": bool(self.subject), "email_present": bool(self.email), "email_verified": self.email_verified, "display_name_present": bool(self.display_name), "avatar_present": bool(self.avatar_url)}


# Define the port a future live provider adapter or a focused mock must implement.
class OAuthProviderPort(Protocol):
    # Expose static provider metadata without exposing any configured credential values.
    spec: ProviderSpec

    # Build a provider authorization URL from caller-owned state, nonce, and callback data.
    def authorization_url(self, *, redirect_uri: str, state: str, nonce: str, pkce_challenge: str | None) -> str:
        # Protocol methods have no implementation because concrete transports remain integration-owned.
        ...

    # Exchange one authorization code and return only allowlisted identity fields.
    def exchange_code(self, *, code: str, redirect_uri: str, expected_nonce: str | None, pkce_verifier: str | None) -> VerifiedIdentity:
        # Live adapters must verify signatures, issuer, audience, expiry, and applicable nonce/PKCE before returning.
        ...


# Define the minimal canonical-user lookup used by external identity linking.
class CanonicalUserLookup(Protocol):
    # Resolve one durable user record by canonical user id.
    def __call__(self, user_id: str) -> Mapping[str, object] | None:
        # Protocol callables have no implementation because tests inject isolated users.
        ...
