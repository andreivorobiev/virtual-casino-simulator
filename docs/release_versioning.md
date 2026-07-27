# Release versioning

Casino packaged releases use four numbers:

```text
<epoch>.<platform-line>.<product-wave>.<patch>
```

The current release is:

```text
0.9.5.13
```

## What each number means

| Slot | Current | Meaning | When it changes |
| --- | ---: | --- | --- |
| `epoch` | `0` | Product maturity. `0` means private beta / restricted preview. | Bump to `1` only for a real public product launch decision. |
| `platform-line` | `9` | The Casino application platform line inherited from the previous `9.x` history. | Bump only for a broad platform generation change: runtime architecture, storage strategy, API generation, or release model. |
| `product-wave` | `5` | The current accepted product capability wave. | Bump for a large product bundle or LPR that users should understand as a meaningful new wave. |
| `patch` | `13` | Compatible fixes, release mechanics, documentation, and small accepted slices inside the current product wave. | Bump for ordinary safe releases inside the same wave. Reset to `0` when `product-wave` bumps. |

## Migration rule

The old three-number product release `9.5.5` maps to:

```text
0.9.5.5
```

That adds the private-beta `0` epoch in front while preserving the existing platform, wave, and patch meaning.

Historical `v9.x.y` tags stay immutable. New packaged release tags use the four-number form, for example:

```text
v0.9.5.13
```

## Next planned release

The next large Claude LPR is reserved as:

```text
0.9.6.0
```

That means the product-wave slot moves from `5` to `6`, and the patch slot resets from the current patch to `0`.

Do not spend `0.9.6.0` on a small fix, docs-only change, release-retry, or mechanical merge. Those stay within the current wave and use the patch slot.

## Module versions are separate

Independent module versions still use normal three-part module revisions such as `1.60.37` or `9.51.21`.

Do not read a module version as the product release. The product release comes only from the top-level `application` field in `modules/module-manifest.json`.
