"""Facebook identity claim normalization without live provider traffic.

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

# Describe Facebook's approved configuration names and minimum login scopes.
FACEBOOK_SPEC = ProviderSpec(provider_id="facebook", flow="oauth2", scopes=("public_profile", "email"), enabled_env="CASINO_OAUTH_ENABLED_FACEBOOK", client_id_env="CASINO_FACEBOOK_APP_ID", client_secret_env="CASINO_FACEBOOK_APP_SECRET")


# Normalize a required provider subject without reflecting unsafe claim data in failures.
def _required_subject(value) -> str:
    # Reject non-text subjects instead of stringifying arbitrary claim objects.
    if not isinstance(value, str):
        # Raise a generic message that never contains the subject.
        raise ValidationError("Facebook identity subject is invalid")
    # Preserve the required provider subject exactly because it is an opaque compound key.
    subject = value
    # Reject empty, overlong, or control-character subjects before persistence.
    if not subject or len(subject) > 255 or any(not character.isprintable() for character in subject):
        # Raise a generic message that never contains the subject.
        raise ValidationError("Facebook identity subject is invalid")
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
        raise ValidationError("Facebook identity email is invalid")
    # Normalize case and surrounding whitespace for diagnostic consistency.
    email = value.strip().lower()
    # Return no email when the provider omitted the optional claim.
    if not email:
        # Preserve absence without inventing an address.
        return None
    # Reject malformed or overlong values without echoing personal data.
    if len(email) > 320 or email.count("@") != 1 or any(character.isspace() or not character.isprintable() for character in email):
        # Raise a generic message that never contains the address.
        raise ValidationError("Facebook identity email is invalid")
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
        raise ValidationError("Facebook identity display name is invalid")
    # Trim the provider claim before checking its public presentation bound.
    display_name = value.strip()
    # Return no display name when the provider omitted it.
    if not display_name:
        # Preserve absence without deriving a name from email.
        return None
    # Reject overlong or control-character display names.
    if len(display_name) > 200 or any(not character.isprintable() for character in display_name):
        # Raise a generic message that never contains the name.
        raise ValidationError("Facebook identity display name is invalid")
    # Return the bounded display name.
    return display_name


# Read Facebook's optional nested picture URL without retaining the raw claim object.
def _picture_url(claims: Mapping[str, object]) -> str | None:
    # Read the optional picture object defensively.
    picture = claims.get("picture")
    # Return no avatar when the picture claim is not an object.
    if not isinstance(picture, Mapping):
        # Preserve absence without raising on an optional provider field.
        return None
    # Read the nested data object defensively.
    data = picture.get("data")
    # Return no avatar when the nested data claim is not an object.
    if not isinstance(data, Mapping):
        # Preserve absence without retaining the malformed object.
        return None
    # Read the optional nested URL value without stringifying arbitrary objects.
    raw_avatar_url = data.get("url")
    # Ignore non-text optional avatar values.
    if raw_avatar_url is not None and not isinstance(raw_avatar_url, str):
        # Return no avatar rather than failing required identity fields.
        return None
    # Reject control-bearing provider text before trimming can hide unsafe characters.
    if raw_avatar_url is not None and any(not character.isprintable() for character in raw_avatar_url):
        # Return no avatar rather than retaining a parser-normalized variant.
        return None
    # Trim the nested URL before validation.
    avatar_url = (raw_avatar_url or "").strip()
    # Return no avatar when the provider omitted the URL.
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
    # Ignore non-HTTPS, credential-bearing, malformed, or overlong optional avatar data.
    if len(avatar_url) > 2048 or any(character.isspace() for character in avatar_url) or parsed.scheme != "https" or not hostname or username or password or port == 0:
        # Return no avatar rather than failing the required identity fields.
        return None
    # Return the safe bounded avatar URL.
    return avatar_url


# Convert mocked or future Facebook claims into the provider-neutral identity model.
def normalize_facebook_identity(claims: Mapping[str, object]) -> VerifiedIdentity:
    # Reject non-mapping payloads before reading provider fields.
    if not isinstance(claims, Mapping):
        # Raise a generic message without serializing the provider payload.
        raise ValidationError("Facebook identity payload is invalid")
    # Return only allowlisted fields and never infer verified email without an explicit provider assertion.
    return VerifiedIdentity(provider=FACEBOOK_SPEC.provider_id, subject=_required_subject(claims.get("id")), email=_optional_email(claims.get("email")), email_verified=False, display_name=_optional_display_name(claims.get("name")), avatar_url=_picture_url(claims))
