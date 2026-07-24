# Phase 0 localization foundation

GitHub issue #128 locks the metadata and runtime boundary for a 25-locale program. Phase 0 does not add translations: `en-US` and `ru-RU` remain the only selectable resource packs, while the other 23 identities remain `metadata-only`.

## Locked registry

| Rank | Translation identity | Native label | Script | Direction | Formatter identity |
| ---: | --- | --- | --- | --- | --- |
| 1 | `en-US` | English | Latn | LTR | `en-US` |
| 2 | `zh-Hans` | 简体中文 | Hans | LTR | `zh-Hans` |
| 3 | `hi-IN` | हिन्दी | Deva | LTR | `hi-IN` |
| 4 | `es-419` | Español (Latinoamérica) | Latn | LTR | `es-419` |
| 5 | `ar` | العربية | Arab | RTL | `ar` |
| 6 | `fr-FR` | Français | Latn | LTR | `fr-FR` |
| 7 | `bn-BD` | বাংলা | Beng | LTR | `bn-BD` |
| 8 | `pt-BR` | Português (Brasil) | Latn | LTR | `pt-BR` |
| 9 | `ru-RU` | Русский | Cyrl | LTR | `ru-RU` |
| 10 | `id-ID` | Bahasa Indonesia | Latn | LTR | `id-ID` |
| 11 | `ur-PK` | اردو | Arab | RTL | `ur-PK` |
| 12 | `de-DE` | Deutsch | Latn | LTR | `de-DE` |
| 13 | `ja-JP` | 日本語 | Jpan | LTR | `ja-JP` |
| 14 | `pcm-NG` | Naijá | Latn | LTR | `pcm-NG` |
| 15 | `arz-EG` | العامية المصرية | Arab | RTL | `ar-EG` |
| 16 | `ta-IN` | தமிழ் | Taml | LTR | `ta-IN` |
| 17 | `vi-VN` | Tiếng Việt | Latn | LTR | `vi-VN` |
| 18 | `te-IN` | తెలుగు | Telu | LTR | `te-IN` |
| 19 | `ha-NG` | Hausa | Latn | LTR | `ha-NG` |
| 20 | `tr-TR` | Türkçe | Latn | LTR | `tr-TR` |
| 21 | `pnb-PK` | پنجابی | Arab | RTL | `ur-PK` |
| 22 | `sw-KE` | Kiswahili | Latn | LTR | `sw-KE` |
| 23 | `fil-PH` | Filipino | Latn | LTR | `fil-PH` |
| 24 | `mr-IN` | मराठी | Deva | LTR | `mr-IN` |
| 25 | `yue-Hant-HK` | 廣東話（香港繁體） | Hant | LTR | `yue-Hant-HK` |

Translation identity and formatter identity are deliberately separate. The browser runtime falls back to `ar-EG` formatting for Egyptian Arabic and `ur-PK` formatting for Western Punjabi because those formatter identities are supported consistently without renaming the translation locale.

## Readiness and fallback

A registry entry becomes selectable only when `readiness` is `ready`, `uiReady` is true, its complete resource tree exists, key and placeholder parity pass, and the required browser evidence is accepted. Asking for a metadata-only locale resolves to the installed source locale; the document `lang` and `dir` describe the locale actually rendered.

Fallback chains are explicit and terminate at `en-US`. Readiness and review status are separate: `ready` describes technical resource availability, while review metadata records source or human review without claiming linguistic certification.

The locked native labels use compact, bundled OFL-licensed Noto Sans subsets for CJK, Devanagari, Bengali, Tamil, and Telugu glyphs that are not guaranteed on clean hosted Chromium runners. The subsets are local static assets, require no runtime font network access, and cover only the Phase 0 labels; later translation waves must extend the reviewed glyph inventory deliberately.

Browser-local language and number/date preferences continue to use `casino.locale.settings.v1`. Display-language choices are limited to ready packs. Number/date formatting can use any configured formatter identity because formatting does not imply translated interface copy.

## Catalog-driven domains

The manifest owns shared domains only. After `/api/v1/casino/state` loads, `web/app.js` registers each `frontend.i18n_domain` from the live game catalog. Adding a game therefore extends localization diagnostics through its module descriptor rather than a central game allowlist; the game resource is still loaded only when its route mounts.

## Translation-wave visual gates

`tests/visual/visual_matrix.json` records all 25 smoke identities and deep script-family groups for Arabic/RTL, CJK, Indic, Cyrillic, and extended Latin coverage. A future locale cannot become ready until real-backend lobby/catalog and representative-game evidence rejects overflow, clipping, tofu, raw keys, English leakage, bidi-order defects, and inaccessible keyboard focus at the governed viewports.

Phase 0 evidence covers the generic Admin registry and persistence surface in the two installed locales. It does not certify the 23 held translations, language quality, public hosting, deployment, native packaging, provider setup, DNS, billing, or issue #209 enablement.

## Traceability

- `I18N-006`: locked registry, metadata, readiness separation, and safe selection.
- `I18N-007`: persistence, deterministic formatting, deliberate fallback, and catalog-driven domain registration.
- `I18N-008`: planned translation-wave and visual-acceptance contract.
- `TEST-101`: API/static and browser/visual foundation evidence.
