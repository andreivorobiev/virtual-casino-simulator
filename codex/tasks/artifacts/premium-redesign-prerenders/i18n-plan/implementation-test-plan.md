# Implementation and Test Plan

## Phase 0: Requirements and Ownership

- Add `I18N-001`, `I18N-002`, and `I18N-003` to `docs/requirements/requirements.json`.
- Decide whether to add a new `modules/i18n.json`; recommended if resource files and `web/core/i18n.js` become a shared module.
- Confirm module version bump policy:
  - Resource/runtime changes: i18n module or application/tooling, depending on module decision.
  - Admin locale API/UI: admin, core/settings, contracts, tests.
  - Game string extraction: the touched game module and i18n module.
  - Shared controls: autoplay, bots, audio, or core as applicable.

## Phase 1: Runtime and Resources

- Add `web/core/i18n.js` with manifest loading, domain loading, fallback, `t()`, interpolation, locale state, and `Intl` formatting helpers.
- Add `web/i18n/manifest.json`, English resources, and Russian resources for `common` and `shell` first.
- Add a validation script that checks:
  - JSON parse success.
  - Every manifest domain exists for every installed locale.
  - Every non-English locale has the same keys as `en-US`.
  - Placeholder names match English.
  - No translated values are empty unless explicitly allowed.

## Phase 2: Locale Persistence

- Extend `casino/core/settings.py` with locale defaults modeled after `audio_settings()`.
- Add `GET /api/v1/admin/locale-settings` and `POST /api/v1/admin/locale-settings`.
- Update `contracts/openapi/admin.v1.yaml` and compatibility digests.
- Persist in `data/settings/locale.json`.
- Use additive optional v1 behavior only; old clients keep working.

Suggested settings shape:

```json
{
  "schema_version": "9.1.0",
  "language": "en-US",
  "format_locale": "en-US",
  "use_browser_locale": false,
  "currency_code": "USD",
  "currency_display": "symbol"
}
```

## Phase 3: Shell, Shared Core, and Admin

- Load `common` and `shell` before rendering `app.js`.
- Extract shell HTML strings from `web/index.html` by either rendering after i18n init or replacing static text with `data-i18n` updates.
- Replace `money()` with `formatMoney()` while keeping fake-money semantics.
- Extract Admin HTML and `admin.js` strings to `admin.json`.
- Add `Language & Locale` tab in Admin.
- Extract `web/core/autoplay.js` and `web/core/bots.js` strings to shared core domains.

## Phase 4: Games

Use one worker per game. Each worker owns one `web/games/<game>.js` plus `web/i18n/<locale>/games/<game>.json`.

Per-game steps:

- Add a domain load before mount.
- Replace visible literals with `t()` calls.
- Convert dynamic phrases to named placeholder templates.
- Preserve all API payload values, ids, test ids, and class names.
- Add an exported `rerenderLocale()` or subscribe to `casino-locale-changed` without remounting.
- Ensure local game variables survive language switching.

Game-specific care:

- Roulette: keep board labels short; map catalog labels only for display.
- Slots: separate symbol ids from symbol display names.
- Keno: selected number set must survive rerender.
- Bingo: decide whether `FREE` is traditional or localized.
- Blackjack: map statuses/outcomes only at display time.
- Baccarat: keep payload bet types raw; translate visible labels.

## Phase 5: Tests

API tests:

- `API-I18N-001`: locale settings GET returns defaults with standard envelope.
- `API-I18N-002`: POST saves supported locale and format locale.
- `API-I18N-003`: unsupported locale falls back or returns a standard validation error.
- `API-I18N-004`: app state and existing admin endpoints remain unchanged for old clients.

Browser tests:

- `BR-I18N-LOBBY-001`: lobby/nav/wallet strings switch English to Russian without navigation.
- `BR-I18N-ADMIN-001`: Admin Language/Locale saves, reloads, and restores.
- `BR-I18N-GAMESTATE-ROU-001`: roulette bet slip, chip selection, balance, and result region survive switching.
- `BR-I18N-GAMESTATE-KENO-001`: selected Keno numbers survive switching.
- `BR-I18N-AUTO-001`: autoplay status and stop button survive switching.
- `BR-I18N-LAYOUT-001`: Russian labels fit at 1080p and mobile smoke sizes.

Static validation:

- Add `python scripts/validate_i18n.py`.
- Include it in the required validation set for i18n PRs.
- Keep `scripts/check_comment_density.py` passing for any touched JavaScript/Python.

## Phase 6: Top-20 Expansion

- Add one locale folder at a time.
- Track translation completeness by domain.
- Add pseudolocale before large rollout if possible, for example `en-XA`.
- Use `dir` from manifest for RTL; do not enable RTL locales until shell, admin, and games have layout smoke coverage.
- Keep `en-US` as the source locale for key parity and fallback.

## Conflict-Avoidance Worker Split

1. Runtime/settings worker owns `web/core/i18n.js`, manifest, settings endpoints, contracts, and validation script.
2. Shell worker owns `web/index.html`, `web/app.js`, `web/core/ui.js`, and `common`/`shell` resources.
3. Admin worker owns `web/admin.html`, `web/admin.js`, and `admin` resources.
4. Shared controls worker owns `web/core/autoplay.js`, `web/core/bots.js`, and related resources.
5. Six game workers own one game each.
6. Tests worker owns `tests/run_tests.py` after implementation workers expose stable selectors.

Only stack branches if two workers must touch the same file, especially `web/core/i18n.js`, `web/core/ui.js`, `web/admin.js`, and `tests/run_tests.py`.

