"""Static local, Google, and Facebook provider definitions for issue #70.

Requirements: OAUTH-001 and OAUTH-005.
"""

# Import the public Facebook provider definition and claim normalizer.
from casino.core.oauth.providers.facebook import FACEBOOK_SPEC, normalize_facebook_identity
# Import the public Google provider definition and claim normalizer.
from casino.core.oauth.providers.google import GOOGLE_SPEC, normalize_google_identity
# Import the unchanged local-login provider definition.
from casino.core.oauth.providers.local import LOCAL_SPEC

# Collect supported providers in deterministic diagnostic and UI order.
PROVIDER_SPECS = (LOCAL_SPEC, GOOGLE_SPEC, FACEBOOK_SPEC)
# Index supported providers by their exact lower-case identifiers.
PROVIDER_SPECS_BY_ID = {spec.provider_id: spec for spec in PROVIDER_SPECS}


# Return one supported provider definition without normalizing unknown identifiers.
def get_provider_spec(provider: str):
    # Import the standard validation error lazily so this package stays dependency-light.
    from casino.errors import ValidationError

    # Reject non-text, unsupported, or case-drifted identifiers before path or storage use.
    if not isinstance(provider, str) or provider not in PROVIDER_SPECS_BY_ID:
        # Raise a value-free error so arbitrary input is never reflected into diagnostics.
        raise ValidationError("Unsupported identity provider")
    # Return the immutable static provider definition.
    return PROVIDER_SPECS_BY_ID[provider]


# Export only stable provider metadata and allowlisted normalizers.
__all__ = ["FACEBOOK_SPEC", "GOOGLE_SPEC", "LOCAL_SPEC", "PROVIDER_SPECS", "get_provider_spec", "normalize_facebook_identity", "normalize_google_identity"]
