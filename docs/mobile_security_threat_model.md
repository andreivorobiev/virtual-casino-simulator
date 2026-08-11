# Mobile client security and lifecycle threat model

Issue #183 introduces a source-complete core transport and session boundary without treating a WebView as a trusted credential store. The browser/PWA cookie path remains unchanged. Native session material exists only inside platform storage and native networking code. Native system-browser OAuth navigation and callback handoff are not implemented by this slice.

## Authorities and protected assets

- The server owns account, session, wallet, game, and settlement truth.
- Android owns one AES-GCM record whose key remains in Android Keystore.
- iOS owns one `ThisDeviceOnly`, non-synchronizing Keychain record.
- Shared JavaScript receives public API data but never the bearer, CSRF proof, guest browser nonce, vault record, or deep-link replay inventory.
- The signed local bundle owns UI and route code; external HTTP pages open outside the WebView.

## Threats and controls

| Threat | Required control |
| --- | --- |
| Cookie/bearer authority confusion | Browser uses host-only cookie plus double-submit CSRF. Native rejects Cookie and uses OS-vault bearer plus matching CSRF. |
| JavaScript credential theft | Native strips credential fields from every session-shaped response; scoped transport recursively rejects residual exact credential keys. |
| Cross-origin or cleartext exfiltration | Backend config requires one HTTPS origin. Server native request classification is default-off and exact, while browser CORS is always disabled and every API preflight is rejected. Native redirects, caches, and arbitrary destinations are forbidden. |
| Account-switch ABA | Monotonic local vault generation is independent of server session generation and advances on each credential commit or clear. |
| Dual reusable rotation credentials | The server replaces bearer, CSRF, and server generation atomically in the provider transaction. A lost response may require login but cannot preserve both credentials. |
| Stale UI or money replay | Every request is vault-generation bound; background/network/foreground/process changes invalidate work. No money mutation is automatically retried. |
| Deep-link theft or replay | Exact HTTPS host/routes only; bearer is removed from history into module memory; native stores only a bounded digest fingerprint; duplicate or unknown state fails closed. |
| Key/value rollback or backup | Android backup is disabled and the record is encrypted with Keystore. iOS Keychain uses this-device-only, non-sync accessibility. |
| Proxy or malformed API response leakage | Both native implementations require a bounded JSON object envelope and never forward raw malformed proxy/server text. |

## Lifecycle order

1. Validate public build configuration and configure the native origin binding.
2. Read platform connectivity and keep mutations closed.
3. Probe the OS-vault session against the minimal native v2 endpoint.
4. Publish the scoped API hook and load the unchanged shared application.
5. After reconnect or foreground, probe first and call the existing authoritative PWA reconnect path before removing the closed state.
6. For account switch, revoke and verify the predecessor, clear the vault, rebind the cleared generation, then create the new session.

## Evidence boundary

Host-runnable Node and Python tests prove parsing, transport descriptors, configuration, session compare-and-swap, lifecycle generations, secret-free envelopes, source wiring, and native platform policy text. They do not prove native OAuth system-browser/callback handoff, an installable signed application, an OS security implementation on a physical device, App/Universal Link association files served by the public host, store review, or production enablement. OAuth handoff remains #183 and platform evidence remains #184, #185, and #195. This slice progresses #183 and must not close those issues.
