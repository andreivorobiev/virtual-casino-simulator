# TiltSeven marketing site

This folder contains a repository-only static website scaffold for a future
TiltSeven root-domain experience.

The gaming simulator remains a separate application at
`https://casino.tiltseven.com`.

Nothing in this directory authorizes upload, hosting, DNS, TLS, provider,
billing, public-launch, or deployment changes. The checked files are review
artifacts until a separate owner-approved publication packet is completed.

## Current scope

- Brand-forward landing page for TiltSeven in English and Russian.
- Static HTML/CSS only; no build step, JavaScript, trackers, payment widgets, or third-party runtime dependencies.
- Hard safety language: play tokens only, no cash value, no deposits, no purchases, no withdrawals, no redemptions, no prizes, and no transferable value.
- Repository evidence only; no live hosting target is selected or changed here.

## Files

- `index.html` — page content and semantic structure.
- `ru/index.html` — Russian page content with the same safety boundary.
- `styles.css` — responsive visual system and layout.
- `assets/tiltseven-mark.svg` — local brand mark used by the page.
- `deployment.md` — owner-gated future publication checklist.

## Visual gates for review

- Desktop primary: 1920x1080.
- Desktop compact: 1440x900.
- Tablet: 1024x900.
- Mobile: 390x844.

The page should show no horizontal overflow, clipped primary calls to action, real-money wording, third-party dependency failures, or inaccessible link labels at those viewports.

The governed surface is `marketing_site` in
`tests/visual/visual_matrix.json`. Hosted Browser acceptance produces eight
`after-pass-marketing-site-*.png` images plus matching provenance sidecars:
both locales at all four viewports.
