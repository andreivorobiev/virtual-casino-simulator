# Capacitor mobile client foundation

This directory contains the repo-owned source foundation for issues #183, #184, #185, and #195. Version `0.2.0` adds a native security and lifecycle boundary around the existing browser product. The independently governed repository module begins at `mobile` module version `1.0.0`; that governance version is intentionally distinct from the installable package version.

The core transport and session slice is source-complete and host-testable. It is not a complete native OAuth, signed-device, or store-release claim. Native system-browser OAuth callback/handoff work remains in #183; Android device/App-Link evidence remains #184, iOS device/Universal-Link evidence remains #185, and cross-platform release evidence remains #195. No provider, DNS, signing, store, public-launch, or production setting is changed here.

## Browser and native authorities

Browser and PWA requests retain the existing host-only session cookie and same-origin double-submit CSRF flow. The native runtime does not rewrite global `fetch`. Shared API code selects an injected Request-compatible native transport only when the signed Capacitor entry point publishes it.

Native requests use an opaque bearer and the matching per-session CSRF proof from Android Keystore-encrypted storage or iOS Keychain. Cookies, JavaScript-authored Authorization/CSRF/guest-proof headers, arbitrary public headers, redirects, caches, foreign origins, and automatic money-action retries are rejected. Login, guest, rotation, current-user, and probe responses are stripped in native code, then recursively checked again before shared JavaScript can receive them.

Server session generation and local vault generation are separate. Server generation is used only for atomic rotation compare-and-swap. The monotonic local vault generation advances on credential issue, replacement, clear, and authoritative 401; it never takes a server value, so switching from account A to account B cannot create an ABA match for a late response.

## Configuration contract

Every build accepts exactly three public fields:

```json
{
  "environment": "development",
  "backendBaseUrl": "https://casino.tiltseven.com",
  "nativeOrigins": [
    "capacitor://localhost",
    "https://localhost"
  ]
}
```

The backend must be one HTTPS origin without credentials, path, query, or fragment. The generated Capacitor origins are exact and complete. Unknown or secret-like fields fail closed. `CASINO_MOBILE_ORIGINS` classifies direct OS-network requests only: browser CORS stays disabled, every API preflight is rejected, and native responses emit no cross-origin read authority.

Android's release source permits no cleartext. Its debug source uses an explicit network security file limited to `localhost`, `127.0.0.1`, and `10.0.2.2`, while committed runtime configuration still requires HTTPS.

Never put passwords, tokens, signing keys, certificates, private endpoints, provider credentials, or production secrets in mobile configuration or bundled assets.

## Lifecycle and links

Cold start, process restore, foreground, reconnect, connectivity edges, clock rollback, and account switch require a native session probe. Foreground and reconnect then call the existing authoritative PWA reconnect boundary before controls reopen. Background prevents new mutations; stale completions cannot repaint. Money actions are never queued or retried automatically.

Only exact owned HTTPS account links are accepted. Enrollment and password-reset bearers move into module-only memory and are removed from WebView history immediately. A bounded digest-only replay inventory lives in the OS vault. Unknown routes, authorities, fields, duplicate query keys, fragments, malformed bearer material, and callback state/nonce additions fail closed.

Provider OAuth remains disabled by default. Programmatic provider navigation, system-browser callback return, and native callback state/nonce handoff are deliberately outside this slice and remain explicit #183/#184/#185/#195 work rather than an implied mobile capability.

## Reproducible host checks

From this directory with the pinned Node and pnpm versions:

```powershell
pnpm install --frozen-lockfile
pnpm run validate
pnpm run build:ci
pnpm run sync:ci
pnpm run check
```

Repository CI runs the pure Node tests without installing mobile packages, plus the Python/API/contract/security gates. Android compilation still requires a supported JDK and Android SDK. iOS compilation and simulator evidence require macOS, Xcode, and the governed signing boundary.

The complete source policy and explicit evidence limits are in `docs/mobile_security_threat_model.md` and `contracts/compatibility/mobile-client-security.json`.
