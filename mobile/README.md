# Capacitor mobile foundation

This directory implements the bounded Phase 1 foundation approved by GitHub issue #188. It packages the existing `web/` product into reproducible Capacitor iOS and Android projects without changing browser source behavior or the frozen `/api/v1` and `/api/v2` paths.

## Version and toolchain

- Mobile foundation version: `0.1.0` (the private package version in `package.json`).
- Package manager: pnpm `11.7.0`.
- Node.js: `22` or newer.
- Capacitor core, CLI, Android, and iOS: `8.4.2`.
- Native lifecycle plugins are pinned independently in `package.json` and locked transitively in `pnpm-lock.yaml`.
- The only dependency build script permitted by `pnpm-workspace.yaml` is the pinned platform-specific `esbuild` binary installer.

This lane does not create a formal packaged application release and does not alter the aggregate module manifest owned by the separate #77 integration lane. The packaged application release was `9.1.1` when this foundation landed (2026-07-14); for the current release see `modules/module-manifest.json` (`application`).

> **Status: unverified against the current backend.** This foundation has not been revalidated since it landed, while the backend has since added the deployment request-integrity policy (exact-Origin checking, per-session double-submit CSRF, SameSite session cookies) and the frontend added a service worker. The cross-origin `fetch` rewrite described below has not been demonstrated end to end against a deployed backend, and no CI workflow builds or tests this directory. Treat the runtime claims here as design intent, not verified behavior.

## Configuration contract

Every build requires a JSON configuration file with exactly these public fields:

```json
{
  "environment": "development",
  "backendBaseUrl": "https://replace-with-an-approved-backend.example"
}
```

`backendBaseUrl` must be an HTTPS origin with no credentials, path, query, or fragment. The only HTTP exception is an explicit `allowInsecureLocalDevelopment: true` build targeting `localhost`, `127.0.0.1`, or the Android emulator bridge `10.0.2.2`. Missing, unsafe, malformed, or secret-like configuration fails before the shared app loads. Environment-specific `dist/` and synced native web assets are ignored by Git.

Android enables cleartext transport only in its debug source set so the explicit emulator bridge can work; release builds retain the platform HTTPS default. Android application backup is disabled as a conservative foundation for later secure-session work.

Never put passwords, tokens, signing keys, certificates, private endpoints, or production secrets in these files. Native secure session storage is a later #187 phase and is intentionally not claimed by this foundation.

## Reproducible commands

Run from this directory with Node and pnpm available:

```powershell
pnpm install --frozen-lockfile
pnpm run validate
pnpm run build:ci
pnpm run sync:ci
pnpm run check
```

For an approved environment, keep its public configuration outside Git and pass only its local path:

```powershell
$env:CASINO_MOBILE_CONFIG = "C:\secure-local-path\casino-mobile.json"
pnpm run sync
```

Android requires a supported JDK and Android SDK/Android Studio:

```powershell
pnpm run run:android
```

iOS generation and sync can be validated on any Node host, but building or running requires macOS with supported Xcode and CocoaPods/SPM tooling:

```bash
pnpm run run:ios
```

`pnpm run open:android` and `pnpm run open:ios` open the generated projects when their platform IDE exists. Signing, store submission, developer enrollment, remote hosting, and production security mutation are outside #188.

`pnpm run doctor` reports optional platform-tooling readiness separately; it is not part of the host-runnable `pnpm run check` gate because ordinary Linux/Windows CI hosts cannot provide Xcode.

## Implemented native foundations

- The generated native WebView always loads bundled shared assets; `server.url` is deliberately absent.
- Root-relative `/api/` requests are translated to one validated backend origin without changing paths, payloads, response envelopes, or browser behavior.
- Offline state blocks new API actions and never queues or automatically retries ledger-affecting requests.
- Backend transport and 5xx failures show a native-only recoverable status banner without exposing endpoint details.
- Backgrounding blocks new mutation requests while an already-started request may finish; foregrounding refreshes native network status and emits additive lifecycle events.
- Safe-area and dynamic-viewport CSS remains scoped to the Capacitor bundle. Native keyboard events expose measured overlap without modifying shared browser CSS.
- External HTTP(S) links open in the system browser rather than replacing the signed casino WebView.

The native-only banner affects the existing `auth` and `shell_lobby` mobile surfaces and the `VIS-COPY-001`, `VIS-LAYOUT-003`, `VIS-RESPONSIVE-001`, and `VIS-EVIDENCE-001` gates. The frozen visual matrix is not edited by #188; simulator/emulator evidence is required when platform tooling is available.

## Host-tooling limits

Native project generation and host-runnable configuration tests do not prove an installable signed release. Android compilation requires a local JDK and Android SDK. iOS compilation and simulator evidence require macOS/Xcode. Record exact missing tools and the generated/sync evidence in the draft PR rather than weakening platform security settings.
