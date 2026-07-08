# Resource Architecture Proposal

## Goals

- Extract every browser-visible UI string without changing game rules, ledger behavior, bot behavior, autoplay behavior, or `/api/v1` compatibility.
- Keep ownership boundaries aligned with module manifests.
- Allow English and Russian implementation first, then scale to additional locales without one large conflict-prone resource file.
- Preserve current data-testid selectors and test stability.

## Proposed File Layout

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
web/i18n/ru-RU/common.json
web/i18n/ru-RU/shell.json
web/i18n/ru-RU/admin.json
web/i18n/ru-RU/core/autoplay.json
web/i18n/ru-RU/core/bots.json
web/i18n/ru-RU/games/roulette.json
web/i18n/ru-RU/games/slots.json
web/i18n/ru-RU/games/keno.json
web/i18n/ru-RU/games/bingo.json
web/i18n/ru-RU/games/blackjack.json
web/i18n/ru-RU/games/baccarat.json
```

Recommended manifest shape:

```json
{
  "defaultLocale": "en-US",
  "fallbackLocale": "en-US",
  "aliases": {
    "en": "en-US",
    "ru": "ru-RU"
  },
  "locales": [
    {"id": "en-US", "label": "English", "nativeLabel": "English", "dir": "ltr"},
    {"id": "ru-RU", "label": "Russian", "nativeLabel": "Русский", "dir": "ltr"}
  ],
  "domains": [
    "common",
    "shell",
    "admin",
    "core/autoplay",
    "core/bots",
    "games/roulette",
    "games/slots",
    "games/keno",
    "games/bingo",
    "games/blackjack",
    "games/baccarat"
  ]
}
```

## Runtime Shape

`web/core/i18n.js` should expose:

- `initI18n({ domains })`: load manifest, resolve locale, fetch initial domains.
- `t(key, params = {}, domainHint)`: return localized plain text with named interpolation.
- `loadI18nDomain(domain)`: lazy-load a domain before mounting a game.
- `setLocale(locale, { persistLocal = true } = {})`: load active domains and dispatch locale change.
- `getLocaleState()`: current locale, fallback, loaded domains, missing key count.
- `formatNumber(value, options)`, `formatMoney(value)`, `formatDate(value, options)`: wrappers around `Intl`.
- `onLocaleChange(callback)`: subscription helper for mounted modules.

`app.js` should load `common` and `shell` before first render. `admin.js` should load `common` and `admin`. Game loading should call `loadI18nDomain("games/roulette")` before `RouletteGame.mount(...)`.

## Key Naming

Use scoped dot keys inside each domain file:

```text
nav.lobby
wallet.balance
toast.fakeMoneyAdded
error.navigationFailed
controls.spin
settings.zeroRule.label
settings.zeroRule.normal
result.noSpinYet
result.rolled
history.latest
tableHeaders.player
```

Do not include domain names inside domain files unless a cross-domain file is intentionally shared. For example, `web/i18n/en-US/games/roulette.json` should use `controls.spin`, not `roulette.controls.spin`.

Use keys for concepts, not source code locations. If a phrase moves from a panel to a toolbar, the key should survive.

## Formatting and Placeholders

Use named placeholders:

```json
{
  "wallet.balance": "Balance: {amount}",
  "result.rolled": "Rolled {number}",
  "result.settlement": "{label}: {outcome}, credit {amount}"
}
```

Validation should fail when translated placeholders differ from English. A future `scripts/validate_i18n.py` can compare every locale against `en-US`, verify JSON syntax, verify manifest domains, and report missing keys.

For pluralization, start with explicit singular/plural keys for English/Russian if needed in phase one:

```text
history.handCount.one
history.handCount.few
history.handCount.many
history.handCount.other
```

The runtime can later grow CLDR plural rules through `Intl.PluralRules` without changing existing keys.

## Static, Dynamic, and Generated Strings

Static strings:

- HTML shell title, brand, wallet button, Admin sidebar labels.
- Game titles, panel headings, control labels, option labels, empty states.
- Table headers and captions.

Dynamic templates:

- Balance, cost, payout, selected spots, call counts, round status, result summaries.
- Toasts and speech strings.
- Admin diagnostics such as active autoplay count and requirement totals.

Generated from backend or game state:

- Player names, bot strategy labels, round ids, bet ids, API enum values, card ranks, drawn numbers, and ledger transaction types.
- These should not be translated at the transport level in phase one. The UI may map known enum display values through resource keys while preserving raw values for APIs and tests.

## Fallback and Missing Keys

Fallback order:

1. Active locale domain.
2. Active locale `common`.
3. Primary-language alias, if installed.
4. `en-US` matching domain.
5. `en-US/common`.
6. The key itself.

The runtime should log missing keys through the existing client logger in development/test mode, but should not interrupt gameplay.

## Security

Translations are plain text. Any string inserted via `innerHTML` must be escaped with `safe(t(...))`, or the code should render DOM text nodes. Avoid resource-provided markup. If a later design needs markup, use a reviewed `.html` key suffix and a very small allowlist.

## Top-20 Language Scalability

After English/Russian is stable, add locale folders one language at a time. Suggested twenty-locale target list:

```text
en-US, ru-RU, es-ES, es-419, zh-CN, hi-IN, ar-SA, pt-BR, bn-BD, fr-FR,
de-DE, ja-JP, ko-KR, id-ID, tr-TR, vi-VN, it-IT, pl-PL, nl-NL, th-TH
```

`ar-SA` introduces right-to-left requirements. Treat RTL support as a deliberate layout-validation milestone, not a silent resource-only addition.
