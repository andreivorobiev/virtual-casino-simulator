# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Google identity claim normalization without live provider traffic.

Requirements: OAUTH-005 and USER-001.
"""

# Import mapping types so mocked claim objects can be validated without an SDK dependency.
from typing import Mapping
# Import URL parsing so avatar values can be restricted to bounded HTTPS URLs.
from urllib.parse import urlsplit

# Import secret-safe identity and provider records.
from casino.core.oauth.models import ProviderSpec, VerifiedIdentity
# Import the standard validation error used by future API envelope integration.
from casino.errors import ValidationError

# Describe Google's approved configuration names and minimum OpenID Connect scopes.
GOOGLE_SPEC = ProviderSpec(provider_id="google", flow="oauth2_oidc", scopes=("openid", "email", "profile"), enabled_env="CASINO_OAUTH_ENABLED_GOOGLE", client_id_env="CASINO_GOOGLE_CLIENT_ID", client_secret_env="CASINO_GOOGLE_CLIENT_SECRET")


# Normalize a required provider subject without reflecting unsafe claim data in failures.
def _required_subject(value) -> str:
    # Reject non-text subjects instead of stringifying arbitrary claim objects.
    if not isinstance(value, str):
        # Raise a generic message that never contains the subject.
        raise ValidationError("Google identity subject is invalid")
    # Preserve the required provider subject exactly because it is an opaque compound key.
    subject = value
    # Reject empty, overlong, or control-character subjects before persistence.
    if not subject or len(subject) > 255 or any(not character.isprintable() for character in subject):
        # Raise a generic message that never contains the subject.
        raise ValidationError("Google identity subject is invalid")
    # Return the bounded opaque subject.
    return subject


# Normalize an optional provider email without treating it as an account-linking key.
def _optional_email(value) -> str | None:
    # Return no email when the provider omitted the optional claim.
    if value is None:
        # Preserve absence without inventing an address.
        return None
    # Reject non-text email claims instead of stringifying arbitrary objects.
    if not isinstance(value, str):
        # Raise a generic message that never contains the address.
        raise ValidationError("Google identity email is invalid")
    # Normalize case and surrounding whitespace for diagnostic consistency.
    email = value.strip().lower()
    # Return no email when the provider omitted the optional claim.
    if not email:
        # Preserve absence without inventing an address.
        return None
    # Reject malformed or overlong values without echoing personal data.
    if len(email) > 320 or email.count("@") != 1 or any(character.isspace() or not character.isprintable() for character in email):
        # Raise a generic message that never contains the address.
        raise ValidationError("Google identity email is invalid")
    # Return the normalized optional email.
    return email


# Normalize a bounded optional display string.
def _optional_display_name(value) -> str | None:
    # Return no display name when the provider omitted the optional claim.
    if value is None:
        # Preserve absence without deriving a name from email.
        return None
    # Reject non-text display-name claims instead of stringifying arbitrary objects.
    if not isinstance(value, str):
        # Raise a generic message that never contains the name.
        raise ValidationError("Google identity display name is invalid")
    # Trim the provider claim before checking its public presentation bound.
    display_name = value.strip()
    # Return no display name when the provider omitted it.
    if not display_name:
        # Preserve absence without deriving a name from email.
        return None
    # Reject overlong or control-character display names.
    if len(display_name) > 200 or any(not character.isprintable() for character in display_name):
        # Raise a generic message that never contains the name.
        raise ValidationError("Google identity display name is invalid")
    # Return the bounded display name.
    return display_name


# Normalize an optional HTTPS avatar URL without fetching it.
def _optional_avatar_url(value) -> str | None:
    # Return no avatar URL when the provider omitted the optional claim.
    if value is None:
        # Preserve absence without supplying a fallback asset.
        return None
    # Ignore non-text optional avatar data.
    if not isinstance(value, str):
        # Return no avatar rather than stringifying arbitrary objects.
        return None
    # Reject control-bearing provider text before trimming can hide unsafe characters.
    if any(not character.isprintable() for character in value):
        # Return no avatar rather than retaining a parser-normalized variant.
        return None
    # Trim the provider claim before URL parsing.
    avatar_url = value.strip()
    # Return no avatar URL when the provider omitted it.
    if not avatar_url:
        # Preserve absence without supplying a fallback asset.
        return None
    # Start protected parsing so malformed optional URLs are safely ignored.
    try:
        # Parse the URL without contacting the remote host.
        parsed = urlsplit(avatar_url)
        # Read authority fields while the parser can report malformed bracket syntax.
        hostname = parsed.hostname
        # Read optional credentials only to reject them.
        username = parsed.username
        # Read optional credentials only to reject them.
        password = parsed.password
        # Read the optional port so malformed or out-of-range authority text fails closed.
        port = parsed.port
    # Ignore malformed optional avatar URLs.
    except ValueError:
        # Return no avatar rather than failing required identity fields.
        return None
    # Reject non-HTTPS, credential-bearing, malformed, or overlong avatar URLs.
    if len(avatar_url) > 2048 or any(character.isspace() for character in avatar_url) or parsed.scheme != "https" or not hostname or username or password or port == 0:
        # Ignore unsafe optional avatar data rather than failing identity authentication.
        return None
    # Return the safe bounded avatar URL.
    return avatar_url


# Convert mocked or future verified Google claims into the provider-neutral identity model.
def normalize_google_identity(claims: Mapping[str, object]) -> VerifiedIdentity:
    # Reject non-mapping payloads before reading provider fields.
    if not isinstance(claims, Mapping):
        # Raise a generic message without serializing the provider payload.
        raise ValidationError("Google identity payload is invalid")
    # Return only allowlisted identity fields and never retain tokens or raw claims.
    return VerifiedIdentity(provider=GOOGLE_SPEC.provider_id, subject=_required_subject(claims.get("sub")), email=_optional_email(claims.get("email")), email_verified=claims.get("email_verified") is True, display_name=_optional_display_name(claims.get("name")), avatar_url=_optional_avatar_url(claims.get("picture")))
