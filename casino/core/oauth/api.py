"""HTTP routes for invite-only Google and Facebook authentication.

Requirements: AUTH-002, OAUTH-001, OAUTH-002, OAUTH-003, OAUTH-004,
OAUTH-007, OAUTH-008, OAUTH-009, OAUTH-010, and TEST-045.
"""

# Import mapping types so tests can inject isolated provider configuration.
from typing import Mapping

# Import the canonical Admin guard for direct-router diagnostic protection.
from casino.core import auth
# Import secret-safe configuration diagnostics.
from casino.core.oauth.configuration import load_oauth_configuration, oauth_diagnostics
# Import the invite-only orchestration boundary.
from casino.core.oauth.service import OAuthService


# Build the Admin diagnostic payload without credential or provider-response values.
def provider_diagnostic_payload(environ: Mapping[str, object] | None = None) -> dict:
    # Load the current or injected configuration snapshot.
    configuration = load_oauth_configuration(environ)
    # Return only explicitly allowlisted readiness facts in stable catalog order.
    return {"providers": [diagnostic.as_dict() for diagnostic in oauth_diagnostics(configuration)]}


# Register exact v2 OAuth routes while preserving frozen v1 unchanged.
def register(router, environ: Mapping[str, object] | None = None, service: OAuthService | None = None) -> None:
    # Construct the production service once unless focused tests supplied a mock.
    oauth = OAuthService(environ=environ) if service is None else service

    # Publish boolean-only provider availability for the login screen.
    @router.get(r"/api/v2/auth/oauth/providers")
    # Return no client ids, callbacks, flags, credentials, or configuration problems.
    def oauth_public_providers(body, query, context):
        # Delegate the current fail-closed availability projection.
        return oauth.public_provider_status()

    # Begin provider sign-in or explicit authenticated account linking.
    @router.post(r"/api/v2/auth/oauth/(?P<provider>google|facebook)/start")
    # Persist one browser-bound expiring flow before returning its navigation URL.
    def oauth_start(body, query, provider, context):
        # Delegate all provider, action, confirmation, rate, and owner policy.
        return oauth.start(provider, body, context)

    # Complete one provider callback and request a safe same-origin 303 response.
    @router.get(r"/api/v2/auth/oauth/(?P<provider>google|facebook)/callback")
    # Consume state before exchange and authenticate only a prelinked active user.
    def oauth_callback(body, query, provider, context):
        # Delegate duplicate-aware query validation and transactional completion.
        return oauth.callback(provider, query, context)

    # Return boolean link state to the authenticated account surface.
    @router.get(r"/api/v2/auth/oauth/links")
    # Expose no provider subjects, claims, tokens, or canonical identifiers.
    def oauth_links(body, query, context):
        # Delegate canonical authenticated ownership validation.
        return oauth.link_status(context)

    # Remove one provider binding only after authenticated explicit confirmation.
    @router.post(r"/api/v2/auth/oauth/(?P<provider>google|facebook)/unlink")
    # Preserve local-password access and revoke only matching provider sessions.
    def oauth_unlink(body, query, provider, context):
        # Delegate transactional unlink and safe session rollback behavior.
        return oauth.unlink(provider, body, context)

    # Retain detailed but secret-safe readiness only on the Admin surface.
    @router.get(r"/api/v2/admin/oauth/providers")
    # Return configured readiness facts to Admin identities only.
    def oauth_provider_diagnostics(body, query, context):
        # Repeat role enforcement for direct router dispatch tests.
        auth.require_admin(context.get("user") or {})
        # Build diagnostics at request time without provider network access.
        return provider_diagnostic_payload(environ)
