"""Static metadata for the existing local password provider.

Requirements: OAUTH-001.
"""

# Import the immutable provider definition shared by diagnostics and integration code.
from casino.core.oauth.models import ProviderSpec

# Describe local password login as always available and unrelated to OAuth configuration.
LOCAL_SPEC = ProviderSpec(provider_id="local", flow="password", enabled_by_default=True)
