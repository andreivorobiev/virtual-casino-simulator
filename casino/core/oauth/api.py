"""Admin-only HTTP integration for disabled OAuth provider diagnostics.

Requirements: OAUTH-001, OAUTH-002, and TEST-045. This module registers no
authorization, callback, exchange, linking, signup, or provider-transport route.
"""

# Import mapping types so focused tests can inject inert environment snapshots.
from typing import Mapping

# Import the canonical auth guard so direct router dispatch also enforces Admin access.
from casino.core import auth
# Import the disabled configuration loader and its allowlisted diagnostic projection.
from casino.core.oauth.configuration import load_oauth_configuration, oauth_diagnostics


# Build the Admin-only diagnostic payload without returning credential values or raw errors.
def provider_diagnostic_payload(environ: Mapping[str, object] | None = None) -> dict:
    # Load an inert snapshot from the process environment or a focused injected mapping.
    configuration = load_oauth_configuration(environ)
    # Return only the explicitly allowlisted diagnostic dictionaries in stable catalog order.
    return {"providers": [diagnostic.as_dict() for diagnostic in oauth_diagnostics(configuration)]}


# Register the single disabled-foundation diagnostic route on the shared API router.
def register(router, environ: Mapping[str, object] | None = None) -> None:
    # Attach an Admin-prefixed read-only route without exposing any provider action endpoint.
    @router.get(r"/api/v2/admin/oauth/providers")
    # Return secret-safe configuration and fixed runtime-unavailable facts to Admin users only.
    def oauth_provider_diagnostics(body, query, context):
        # Repeat the role check at the route boundary so direct router tests fail closed.
        auth.require_admin(context.get("user") or {})
        # Build diagnostics at request time while opening no listener or provider connection.
        return provider_diagnostic_payload(environ)
