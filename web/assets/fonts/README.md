# Native-label font subsets

These ten WOFF2 files are exact-text subsets of Google Noto Sans families used only by the locked Phase 0 locale registry. They keep the CJK, Devanagari, Bengali, Tamil, and Telugu native labels legible on clean offline or hosted Chromium installations without fetching fonts at runtime.

The files were obtained from the official Google Fonts CSS API and `fonts.gstatic.com` delivery URLs with only the native-label characters requested. Regular and bold weights are retained because the registry uses both weights. They are licensed under the SIL Open Font License 1.1 in `OFL.txt`.

| File family | Weight | Covered registry labels |
| --- | ---: | --- |
| `noto-sans-locale-cjk*.woff2` | 400, 700 | 简体中文, 日本語, 廣東話（香港繁體） |
| `noto-sans-locale-devanagari*.woff2` | 400, 700 | हिन्दी, मराठी |
| `noto-sans-locale-bengali*.woff2` | 400, 700 | বাংলা |
| `noto-sans-locale-tamil*.woff2` | 400, 700 | தமிழ் |
| `noto-sans-locale-telugu*.woff2` | 400, 700 | తెలుగు |

Do not replace these with a remote stylesheet or broaden the character inventory silently. A future translation wave must add its reviewed glyph inventory and preserve the no-runtime-network boundary.
