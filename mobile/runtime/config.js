// Define the only configuration keys allowed into the signed mobile web bundle.
const ALLOWED_KEYS = new Set(["environment", "backendBaseUrl", "allowInsecureLocalDevelopment"]);
// Define local-only host names that may use HTTP when development explicitly opts in.
const LOCAL_HTTP_HOSTS = new Set(["127.0.0.1", "localhost", "10.0.2.2"]);

// Export strict validation so the build and runtime enforce the same fail-closed contract.
export function validateMobileConfig(value) {
  // Reject arrays, null, and primitive values before reading configuration fields.
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Mobile configuration must be a JSON object.");
  // Reject unknown keys so credentials or accidental secret-bearing fields cannot be bundled.
  for (const key of Object.keys(value)) if (!ALLOWED_KEYS.has(key)) throw new Error(`Unsupported mobile configuration key: ${key}`);
  // Require a short environment label for evidence and build provenance.
  if (typeof value.environment !== "string" || !/^[a-z][a-z0-9-]{0,31}$/.test(value.environment)) throw new Error("environment must be a lowercase label.");
  // Require an explicit backend URL instead of falling back to the native WebView origin.
  if (typeof value.backendBaseUrl !== "string" || value.backendBaseUrl.length === 0) throw new Error("backendBaseUrl is required.");
  // Parse the backend value with the platform URL implementation.
  const backend = new URL(value.backendBaseUrl);
  // Reject embedded credentials because native configuration is not a secret store.
  if (backend.username || backend.password) throw new Error("backendBaseUrl must not contain credentials.");
  // Reject query strings and fragments so only a stable backend origin is configured.
  if (backend.search || backend.hash) throw new Error("backendBaseUrl must not contain a query string or fragment.");
  // Reject path prefixes so frozen API paths retain their exact /api/v1 and /api/v2 meanings.
  if (backend.pathname !== "/") throw new Error("backendBaseUrl must be an origin without a path.");
  // Record whether the explicit local-development escape hatch is enabled.
  const allowsLocalHttp = value.allowInsecureLocalDevelopment === true && LOCAL_HTTP_HOSTS.has(backend.hostname);
  // Require HTTPS except for explicitly opted-in loopback or Android-emulator development.
  if (backend.protocol !== "https:" && !(backend.protocol === "http:" && allowsLocalHttp)) throw new Error("backendBaseUrl must use HTTPS outside explicit local development.");
  // Return only normalized, public configuration values for bundling and runtime use.
  return Object.freeze({ environment: value.environment, backendBaseUrl: backend.origin, allowInsecureLocalDevelopment: allowsLocalHttp });
}
