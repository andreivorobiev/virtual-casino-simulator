# TiltSeven marketing site

This folder contains the static website intended for `https://tiltseven.com` and `https://www.tiltseven.com`.

The gaming simulator remains a separate application at `https://casino.tiltseven.com`.

## Current scope

- Brand-forward landing page for TiltSeven.
- Static HTML/CSS only; no build step, JavaScript, trackers, payment widgets, or third-party runtime dependencies.
- Hard safety language: play tokens only, no cash value, no deposits, no purchases, no withdrawals, no redemptions, no prizes, and no transferable value.
- Deployment target: Midphase/StackCP shared hosting web root for `tiltseven.com`.

## Files

- `index.html` — page content and semantic structure.
- `styles.css` — responsive visual system and layout.
- `assets/tiltseven-mark.svg` — local brand mark used by the page.
- `deployment.md` — DNS, TLS, hosting, and smoke-test notes.

## Visual gates for review

- Desktop primary: 1920x1080.
- Desktop compact: 1440x900.
- Tablet: 1024x900.
- Mobile: 390x844.

The page should show no horizontal overflow, clipped primary calls to action, real-money wording, third-party dependency failures, or inaccessible link labels at those viewports.
