# I18n Locale Plan Handback

Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/4

Scope: proposal only. No production `web/`, `casino/`, `contracts/`, `tests/`, `docs/requirements/`, or `modules/` files were changed.

## Recommendation

Add a small frontend i18n runtime plus JSON resource files under a future `web/i18n/` tree. Use `en-US` as the canonical default locale, `ru-RU` as the first translated locale, and aliases `en` and `ru` for convenience. Keep resources split by app surface and game so implementation workers can extract strings without colliding.

Proposed runtime files:

```text
web/core/i18n.js
web/i18n/manifest.json
web/i18n/en-US/common.json
web/i18n/en-US/shell.json
web/i18n/en-US/admin.json
web/i18n/en-US/core/autoplay.json
web/i18n/en-US/core/bots.json
web/i18n/en-US/games/roulette.json
web/i18n/en-US/games/slots.json
web/i18n/en-US/games/keno.json
web/i18n/en-US/games/bingo.json
web/i18n/en-US/games/blackjack.json
web/i18n/en-US/games/baccarat.json
web/i18n/ru-RU/... same domains ...
```

Key conventions:

- Use stable, semantic, dot-separated keys scoped to the file domain: `nav.lobby`, `wallet.balance`, `result.noSpinYet`, `settings.zeroRule.normal`.
- Do not encode visual placement in keys. Prefer `roulette.controls.spin` over `leftPanel.bigSpinButton`.
- Keep `data-testid`, API ids, CSS classes, enum wire values, and route names out of resources.
- Use named placeholders such as `{amount}`, `{count}`, `{game}`, and validate placeholder parity across locales.
- Treat translations as plain text by default. Escape with `safe()` when inserting through `innerHTML`; avoid HTML in resources except reviewed `.html` keys.
- Fallback order: selected locale domain -> selected locale `common` -> primary language alias -> `en-US` domain -> `en-US/common` -> visible key.

## Admin Language/Locale

Add a dedicated Admin tab near `Audio & Voice`: `Language & Locale`.

Controls:

- App language select: English, Russian, and future installed languages.
- Locale/format select: default to same as language, allow browser default.
- Fake-money format preview using the same balance formatter as the shell.
- Date/time format preview for admin telemetry rows.
- Apply now, Save global default, Reset to browser default.
- Read-only diagnostics: resolved locale, fallback locale, loaded resource domains, missing key count.

Persistence proposal:

- Additive v1 endpoints: `GET /api/v1/admin/locale-settings` and `POST /api/v1/admin/locale-settings`.
- Store server default in `data/settings/locale.json`, modeled after existing audio settings.
- Keep an immediate browser override in `localStorage` so language switches apply before or without a save.
- Resolution order: URL override, localStorage override, saved Admin default, browser language, `en-US`.

## State Preservation

Language changes must not navigate, reload the page, remount a game, reset module variables, or call game state reset APIs. `setLocale()` should load dictionaries, update shell text, and dispatch `casino-locale-changed`. Mounted game modules should expose a lightweight `rerenderLocale()` or reuse their current `render()` against existing in-memory state. Current game state such as roulette open bets, selected Keno spots, blackjack round id, chip selection, and autoplay sessions remains in module variables or server state.

## Samples

Sample entries are in:

- `samples/en-US.json`
- `samples/ru-RU.json`

The Russian sample is intentionally polished but conservative: familiar casino terms are localized where natural and left as known casino terms where over-translation would feel odd.

The sample files use composed keys such as `shell.nav.lobby` so reviewers can read one compact file per locale. In production, the same entries should be split into domain files as described in `resource-architecture.md`; inside `shell.json`, the key would be `nav.lobby`.

## Execution Plan

1. Add proposed future requirements `I18N-001`, `I18N-002`, and `I18N-003`.
2. Add i18n runtime, manifest, English resources, and missing-key validation.
3. Add locale settings persistence and Admin controls.
4. Extract shell, shared core, and admin strings.
5. Extract each game module independently.
6. Add Russian resources and validate parity.
7. Add browser/API tests and layout checks for longer strings.
8. Add top-20 language folders only after the English/Russian path is stable.

## Test Plan

API:

- Verify locale settings GET/POST uses the standard `{ ok, data }` envelope.
- Verify supported locale validation, fallback behavior, and persistence.
- Verify old clients still work with no locale calls.

Browser:

- Switch lobby from English to Russian without route reload.
- Save language in Admin, reload `/` and `/admin`, and confirm persistence.
- Place a roulette bet, switch language, verify bet slip and balance remain.
- Select Keno spots, switch language, verify selected numbers remain.
- Start autoplay, switch language, verify running/stop controls remain usable.
- Verify stable `data-testid` selectors remain unchanged.

## Worker Split

- Runtime/settings worker: `web/core/i18n.js`, `casino/core/settings.py`, admin locale API, contracts, requirements, module versions.
- Shell worker: `web/index.html`, `web/app.js`, `web/core/ui.js`, shell/common resources.
- Admin worker: `web/admin.html`, `web/admin.js`, admin resources, Admin Language/Locale UI.
- Shared controls worker: `web/core/autoplay.js`, `web/core/bots.js`, voice/speech strings.
- One game worker per game: each `web/games/<game>.js` plus that game's locale files.
- Tests worker: `tests/run_tests.py`, i18n validation script, browser/API coverage.

## Open Questions

- Should language be global for the local casino, per browser, or both as proposed?
- Should fake money always display as `$` or use locale-specific currency formatting with a fake-money label?
- Are backend error messages in phase one, or should phase one map only known `error.code` values to localized friendly text?
- Should speech synthesis utterances switch language automatically with the UI locale?
- Should the first top-20 expansion include right-to-left layout validation for Arabic immediately, or after English/Russian hardening?
