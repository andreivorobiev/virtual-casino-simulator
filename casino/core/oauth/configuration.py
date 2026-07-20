"""Disabled-by-default OAuth settings and secret-safe runtime diagnostics.

Requirements: OAUTH-001 and OAUTH-002. This module performs no provider traffic.
"""

# Import process environment access while retaining injectable mappings for tests.
import os
# Import dataclass helpers so credential fields can be excluded from representations.
from dataclasses import dataclass, field
# Import mapping types for isolated configuration tests.
from typing import Mapping

# Import exact callback construction for readiness diagnostics.
from casino.core.oauth.callbacks import build_callback_url
# Import immutable provider metadata.
from casino.core.oauth.models import ProviderSpec
# Import the static provider catalog in stable display order.
from casino.core.oauth.providers import PROVIDER_SPECS
# Import the standard validation error only for safe callback-configuration handling.
from casino.errors import ValidationError

# Accept explicit truthy configuration values without enabling on arbitrary text.
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
# Accept explicit false values and blank defaults without treating them as errors.
FALSE_VALUES = frozenset({"", "0", "false", "no", "off"})


# Hold configured external-provider credential values while suppressing them from repr output.
@dataclass(frozen=True)
class ProviderCredentials:  # Keep configured values available to integration while repr-safe.
    # Store the public client identifier for later integration without diagnostic exposure.
    client_id: str = field(repr=False)
    # Store the provider secret for later integration without diagnostic exposure.
    client_secret: str = field(repr=False)


# Hold one external provider's effective configuration without making it available automatically.
@dataclass(frozen=True)
class ProviderConfiguration:  # Keep one provider's inert effective settings together.
    # Store immutable provider metadata.
    spec: ProviderSpec
    # Record the fail-closed boolean derived from the explicit enable setting.
    enabled_requested: bool
    # Record whether the enable setting used an accepted explicit value.
    enable_flag_valid: bool
    # Store configured credentials while suppressing their values from repr output.
    credentials: ProviderCredentials = field(repr=False)
    # Store the callback base without exposing accidental credentials or malformed input in repr.
    public_base_url: str = field(repr=False)


# Hold the complete provider configuration snapshot without executing provider behavior.
@dataclass(frozen=True)
class OAuthConfiguration:  # Keep the complete inert provider snapshot immutable.
    # Store external provider configurations in deterministic order.
    providers: tuple[ProviderConfiguration, ...]


# Describe one provider's readiness without exposing credentials or personal data.
@dataclass(frozen=True)
class ProviderDiagnostic:  # Publish only allowlisted readiness facts.
    # Store the stable provider identifier.
    provider: str
    # Store the provider flow class for future local/OAuth UI grouping.
    flow: str
    # Store ready, disabled, or misconfigured as the effective safe status.
    status: str
    # Report whether inert configuration is structurally ready for later integration.
    configuration_ready: bool
    # Report whether a registered runtime route and adapter are currently available.
    runtime_available: bool
    # Report whether an operator explicitly requested enablement.
    enabled_requested: bool
    # Report only whether the public client identifier is present.
    client_id_configured: bool
    # Report only whether the provider secret is present.
    client_secret_configured: bool
    # Store the public callback URL only when its configuration is structurally valid.
    callback_url: str | None
    # Store missing environment-variable names rather than their values.
    missing_variables: tuple[str, ...] = field(default_factory=tuple)
    # Store stable problem identifiers rather than raw exception or environment text.
    problems: tuple[str, ...] = field(default_factory=tuple)

    # Convert diagnostics to the plain public shape expected by later Admin integration.
    def as_dict(self) -> dict:
        # Return only allowlisted non-secret configuration facts.
        return {"provider": self.provider, "flow": self.flow, "status": self.status, "configuration_ready": self.configuration_ready, "runtime_available": self.runtime_available, "enabled_requested": self.enabled_requested, "client_id_configured": self.client_id_configured, "client_secret_configured": self.client_secret_configured, "callback_url": self.callback_url, "missing_variables": list(self.missing_variables), "problems": list(self.problems)}


# Read one environment setting as exact text without logging or returning its key/value pair.
def _environment_value(environ: Mapping[str, object], name: str | None) -> str:
    # Return no value when the provider definition has no corresponding setting.
    if not name:
        # Preserve absence for the local provider definition.
        return ""
    # Read the injected or live value without invoking arbitrary string conversion.
    value = environ.get(name, "")
    # Return exact text so credential values are never silently normalized.
    return value if isinstance(value, str) else ""


# Parse one explicit provider enable flag with a fail-closed invalid state.
def _parse_enable_flag(raw_value: str) -> tuple[bool, bool]:
    # Normalize operator-facing flag whitespace and case without touching credentials.
    normalized = raw_value.strip().lower()
    # Enable only on an explicitly approved truthy value.
    if normalized in TRUE_VALUES:
        # Return requested and valid.
        return True, True
    # Keep the provider disabled for approved false or absent values.
    if normalized in FALSE_VALUES:
        # Return not requested and valid.
        return False, True
    # Keep the provider disabled while reporting the invalid setting.
    return False, False


# Load external OAuth configuration without validating, logging, or using credentials.
def load_oauth_configuration(environ: Mapping[str, object] | None = None) -> OAuthConfiguration:
    # Use the live process environment only when the caller did not inject an isolated mapping.
    current_environment = os.environ if environ is None else environ
    # Collect only external-provider configurations while preserving static catalog order.
    provider_configurations = []
    # Iterate over the local and external provider catalog.
    for spec in PROVIDER_SPECS:
        # Skip local password login because it has no OAuth environment configuration.
        if spec.flow == "password":
            # Continue to external providers without modifying local-login behavior.
            continue
        # Read and parse the provider's explicit enable flag.
        enabled_requested, enable_flag_valid = _parse_enable_flag(_environment_value(current_environment, spec.enabled_env))
        # Store credentials without exposing their values through repr output.
        credentials = ProviderCredentials(client_id=_environment_value(current_environment, spec.client_id_env), client_secret=_environment_value(current_environment, spec.client_secret_env))
        # Store the inert configuration snapshot for later diagnostics.
        provider_configurations.append(ProviderConfiguration(spec=spec, enabled_requested=enabled_requested, enable_flag_valid=enable_flag_valid, credentials=credentials, public_base_url=_environment_value(current_environment, "CASINO_OAUTH_PUBLIC_BASE_URL")))
    # Return an immutable configuration snapshot without enabling any provider behavior.
    return OAuthConfiguration(providers=tuple(provider_configurations))


# Build one external provider diagnostic from an inert configuration snapshot.
def _external_provider_diagnostic(configuration: ProviderConfiguration) -> ProviderDiagnostic:
    # Collect missing variable names without collecting or exposing their values.
    missing_variables = []
    # Record absence of the public client identifier.
    if not configuration.credentials.client_id.strip():
        # Append only the setting name from static provider metadata.
        missing_variables.append(configuration.spec.client_id_env)
    # Record absence of the provider secret.
    if not configuration.credentials.client_secret.strip():
        # Append only the setting name from static provider metadata.
        missing_variables.append(configuration.spec.client_secret_env)
    # Record absence of the shared public callback base.
    if not configuration.public_base_url:
        # Append only the canonical environment-variable name.
        missing_variables.append("CASINO_OAUTH_PUBLIC_BASE_URL")
    # Collect stable problem identifiers rather than exception text or supplied values.
    problems = []
    # Record an invalid enable flag separately from other missing configuration.
    if not configuration.enable_flag_valid:
        # Append one stable problem identifier.
        problems.append("invalid_enable_flag")
    # Start without a callback URL until structural validation succeeds.
    callback_url = None
    # Validate a configured public base even while disabled so Operations can prepare safely.
    if configuration.public_base_url:
        # Start protected validation so malformed public settings become diagnostics.
        try:
            # Build the exact provider callback URL without opening a listener or network connection.
            callback_url = build_callback_url(configuration.public_base_url, configuration.spec.provider_id)
        # Convert safe validation failures into one stable public problem code.
        except ValidationError:
            # Record only the problem class and never the configured base value.
            problems.append("invalid_public_base_url")
    # Mark explicitly requested but incomplete or malformed providers as misconfigured.
    if not configuration.enable_flag_valid or (configuration.enabled_requested and (missing_variables or problems)):
        # Store the fail-closed misconfigured status.
        status = "misconfigured"
    # Mark a fully configured explicitly requested provider as ready for later route integration.
    elif configuration.enabled_requested:
        # Store the ready status without enabling routes or network traffic.
        status = "ready"
    # Keep every provider disabled when enablement was not explicitly requested.
    else:
        # Store the safe default status.
        status = "disabled"
    # Report integrated runtime availability only when every explicit setting is ready.
    runtime_available = status == "ready"
    # Return only secret-safe readiness facts.
    return ProviderDiagnostic(provider=configuration.spec.provider_id, flow=configuration.spec.flow, status=status, configuration_ready=status == "ready", runtime_available=runtime_available, enabled_requested=configuration.enabled_requested, client_id_configured=bool(configuration.credentials.client_id.strip()), client_secret_configured=bool(configuration.credentials.client_secret.strip()), callback_url=callback_url, missing_variables=tuple(name for name in missing_variables if name), problems=tuple(problems))


# Return local and external provider diagnostics in deterministic display order.
def oauth_diagnostics(configuration: OAuthConfiguration) -> tuple[ProviderDiagnostic, ...]:
    # Start with local password login as available and unchanged.
    diagnostics = [ProviderDiagnostic(provider="local", flow="password", status="ready", configuration_ready=True, runtime_available=True, enabled_requested=True, client_id_configured=False, client_secret_configured=False, callback_url=None)]
    # Append one fail-closed diagnostic for each configured external provider.
    diagnostics.extend(_external_provider_diagnostic(provider) for provider in configuration.providers)
    # Return an immutable diagnostic collection for future Admin or UI adapters.
    return tuple(diagnostics)
