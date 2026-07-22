"""Versioned Admin, availability, linking, callback, and unlink OAuth routes.

Requirements: OAUTH-001, OAUTH-002, OAUTH-007, OAUTH-008, OAUTH-009, and
OAUTH-010. Provider transport remains inaccessible unless both provider and
independent network-release flags are true.
"""

# Import mapping types for isolated diagnostics and runtime tests.
from typing import Mapping

# Import the canonical Admin guard for direct router dispatch.
from casino.core import auth
# Import secret-safe provider configuration and diagnostic projections.
from casino.core.oauth.configuration import load_oauth_configuration, oauth_diagnostics
# Import the request-scoped orchestration boundary without creating provider transport at import.
from casino.core.oauth.service import OAuthService

# Cache only the provider-neutral service; configuration and adapters remain request-local.
_SERVICE = None


# Build or return the provider-neutral production service lazily.
def configured_service() -> OAuthService:
    # Publish one module-level service only after the first route needs it.
    global _SERVICE
    # Construct no provider adapter, listener, or network call during lazy initialization.
    if _SERVICE is None:
        # Bind the service to the configured shared storage provider.
        _SERVICE = OAuthService()
    # Return the provider-neutral service instance.
    return _SERVICE


# Build the Admin diagnostic payload without returning credential values or raw errors.
def provider_diagnostic_payload(environ: Mapping[str, object] | None = None) -> dict:
    # Load an inert snapshot from the process environment or focused injected mapping.
    configuration = load_oauth_configuration(environ)
    # Return only explicitly allowlisted diagnostic dictionaries in stable order.
    return {"providers": [diagnostic.as_dict() for diagnostic in oauth_diagnostics(configuration)]}


# Register the complete disabled-by-default v2 OAuth surface.
def register(router, environ: Mapping[str, object] | None = None, service: OAuthService | None = None) -> None:
    # Resolve the injected service for tests or lazily configured production service per request.
    def runtime() -> OAuthService:
        # Preserve isolated test dependencies without mutating the module singleton.
        return service if service is not None else configured_service()

    # Attach the Admin-only secret-safe readiness route.
    @router.get(r"/api/v2/admin/oauth/providers")
    # Return allowlisted configuration and independent release facts.
    def oauth_provider_diagnostics(body, query, context):
        # Repeat the role check so direct router tests fail closed.
        auth.require_admin(context.get("user") or {})
        # Build diagnostics at request time while opening no provider connection.
        return provider_diagnostic_payload(environ)

    # Attach anonymous boolean-only provider availability for the login gate.
    @router.get(r"/api/v2/auth/oauth/providers")
    # Return only provider ids and currently released availability booleans.
    def oauth_public_providers(body, query):
        # Delegate current flag and release evaluation without creating an adapter.
        return runtime().public_provider_status()

    # Attach the exact reviewed provider start route for sign-in or explicit linking.
    @router.post(r"/api/v2/auth/oauth/(?P<provider>google|facebook)/start")
    # Start one browser-bound, expiring authorization flow.
    def oauth_start(body, query, provider, context):
        # Delegate strict body, auth, CSRF, rate, configuration, and proof policy.
        return runtime().start(provider, body, context)

    # Attach the exact provider callback route with duplicate-aware raw query values.
    @router.get(r"/api/v2/auth/oauth/(?P<provider>google|facebook)/callback")
    # Complete or recover one provider callback through the state machine.
    def oauth_callback(body, query, provider, context):
        # Delegate strict callback and recoverable exchange policy.
        return runtime().callback(provider, query, context)

    # Attach authenticated boolean-only link status for My Settings/account controls.
    @router.get(r"/api/v2/me/oauth/providers")
    # Return linked and available booleans without subjects or user ids.
    def oauth_link_status(body, query, context):
        # Delegate canonical active local-account and link projection policy.
        return runtime().link_status(context)

    # Attach explicit authenticated provider unlink with provider-session revocation.
    @router.post(r"/api/v2/me/oauth/(?P<provider>google|facebook)/unlink")
    # Revoke provider sessions and remove only the selected link.
    def oauth_unlink(body, query, provider, context):
        # Delegate exact confirmation, local recovery, session, and link policy.
        return runtime().unlink(provider, body, context)
