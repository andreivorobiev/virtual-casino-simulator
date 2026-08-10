# Open-ticket review — 2026-08-10

Source baseline: protected `main` at `ae708003ff8894fbe181174a9c97f5bf8bebf33c`.

GitHub contained 55 open issues and no open pull requests at review time. Because 55 is odd, the selected larger half contains 28 issues. Selection follows the existing stack rank, not implementation convenience. A selected umbrella remains open until its complete acceptance is proven; repository code cannot truthfully satisfy provider-console, DNS, app-store, billing, mailbox, legal-policy, or public-launch decisions.

## Selected larger half

| Rank | Issue | Current disposition |
|---:|---:|---|
| 2 | #431 | Repository-actionable storage refactor; acute destructive create path is already fixed, row-scoped provider cleanup remains. |
| 4 | #433 | Repository-actionable rule-schema enforcement; runtime policy choices must preserve frozen-v1 compatibility and fail closed. |
| 5 | #323 | Repository-actionable performance program; this tranche lands source-bound payload and multiprocess checkpoints. |
| 6 | #333 | Repository controls exist and remain disabled by default; live readiness/provider activation remains external. |
| 8 | #69 | Account foundation is delivered; live mail and unrestricted enrollment remain external launch decisions. |
| 9 | #335 | Disabled-by-default provider signup remains gated by provider readiness and public policy. |
| 10 | #336 | Repository evidence can progress; provider-console revocation/deletion proof remains external. |
| 11 | #209 | Read-only launch dashboard exists; unrestricted launch remains explicitly external and fail closed. |
| 12 | #183 | Native transport/session source is repository-actionable; device/keychain/app-link evidence remains platform-bound. |
| 13 | #168 | All-game deterministic motion contract remains browser-visible implementation and evidence work. |
| 14 | #169 | Roulette authentic pacing and recovery remain browser-visible implementation and evidence work. |
| 15 | #170 | Slots reel motion and recovery remain browser-visible implementation and evidence work. |
| 17 | #74 | Remaining visual, motion, scroll, and refresh acceptance stays browser-gated. |
| 21 | #434 | Repository-actionable governance; this tranche lands the executable descriptor-suite discovery boundary. |
| 22 | #456 | Economics telemetry is partly delivered; complete 46-game economics certification remains. |
| 24 | #432 | Repository-actionable ledger action index and bounded recovery/read paths remain. |
| 27 | #350 | Child implementations are delivered; umbrella closure requires final acceptance reconciliation. |
| 29 | #349 | Manual problem reporting is delivered; publication/privacy remainder stays open unless completed. |
| 30 | #128 | Locale framework exists; 26-locale translation and native-speaker certification remain. |
| 39 | #182 | PWA foundation is delivered; representative Android/iOS install evidence remains. |
| 40 | #184 | Android source exists; reproducible APK/AAB plus device/emulator evidence remains. |
| 41 | #185 | iOS source exists; supported macOS/Xcode build and simulator evidence remains external to this Windows host. |
| 42 | #186 | Store/privacy release evidence requires owner/legal/platform decisions and cannot be inferred from source. |
| 43 | #181 | Mobile umbrella remains open until PWA, Android, and iOS completion evidence all pass. |
| 44 | #187 | Native-app umbrella remains open until platform builds, beta evidence, and policy gates pass. |
| 45 | #195 | Android and iOS build/simulator gate remains a mandatory external-platform acceptance step. |
| 47 | #371 | Repository TiltSeven assets are delivered; domain/mailbox/public cutover remains separately controlled. |
| 55 | #66 | Historical umbrella remains open while selected child programs retain incomplete acceptance. |

## Remaining 27 issues

| Issue | Review disposition |
|---:|---|
| #435 | Controlled-runner hardening remains queued; no secret or runner activation is inferred. |
| #167 | Session-wellness enhancement remains a safe product backlog item. |
| #166 | Admin catalog-curator enhancement remains a safe product backlog item. |
| #165 | Version-aware What's New enhancement remains a safe product backlog item. |
| #161 | Explain-this-outcome receipt remains a safe product backlog item. |
| #162 | Round Replay Theater remains a safe product backlog item. |
| #159 | Practice Rewind remains a safe product backlog item. |
| #160 | Compare Games remains a safe product backlog item. |
| #164 | Personal table profiles remain a safe product backlog item. |
| #158 | Lobby Concierge remains a safe product backlog item. |
| #129 | Vultr staging requires provider/account authority and remains queued. |
| #441 | Comment-policy replacement requires an explicit governance decision and remains queued. |
| #163 | Cross-device session handoff remains a product/security backlog item. |
| #337 | Magic-link login remains gated by mail readiness and remains queued. |
| #488 | Challenge Points and non-traditional-games epic remains queued behind platform design. |
| #154 | Community Bingo remains a game backlog item. |
| #145 | Pai Gow Tiles remains a game backlog item. |
| #489 | Snake Circuit remains under #488. |
| #490 | Durak Duel remains under #488. |
| #491 | Minesweeper Vault remains under #488. |
| #492 | Number Merge remains under #488. |
| #493 | Reversi Arena remains under #488. |
| #494 | Fleet Command remains under #488. |
| #495 | Memory Vault remains under #488. |
| #496 | Codebreaker remains under #488. |
| #497 | Block Drop remains under #488. |
| #498 | Tower Stack remains under #488. |

## Closure rule

The pull request associated with this review may use `Closes` only for a ticket whose full current acceptance is implemented and proven at the exact head. Every other selected ticket must use `Progresses` and retain its explicit remainder. A deployment proves only the released source and production gates; it does not manufacture external provider, device, store, legal, DNS, mailbox, or public-launch evidence.
