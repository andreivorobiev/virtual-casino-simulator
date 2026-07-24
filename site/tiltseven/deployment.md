# TiltSeven deployment notes

Status: draft deployment runbook for the static TiltSeven marketing site.

## Intended routing

- `tiltseven.com` and `www.tiltseven.com` serve the marketing website from Midphase/StackCP shared hosting.
- `casino.tiltseven.com` serves the casino simulator application on the existing casino VPS.
- `luckytilt.com` remains available as a secondary/defensive brand domain until Andrei chooses whether it redirects, hosts a campaign page, or is retired.

## DNS expectations

The root domain should point at the Midphase/StackCP shared hosting IP.

```text
tiltseven.com.      A      185.146.167.200
www.tiltseven.com.  CNAME  tiltseven.com.
casino.tiltseven.com. A    45.63.35.198
```

Mail remains on StackMail for `andrei@tiltseven.com`.

```text
tiltseven.com. MX 10 mx.stackmail.com.
tiltseven.com. TXT "v=spf1 include:spf.stackmail.com a mx -all"
mail.tiltseven.com. CNAME mail.stackmail.com.
```

## TLS expectations

- StackCP Free SSL should be active for `tiltseven.com` and `*.tiltseven.com` before Force HTTPS is relied upon.
- The casino VPS certificate must explicitly include `casino.tiltseven.com` before public links route players there.
- After StackCP activation, allow up to 30 minutes for the shared-hosting load balancers to deploy the certificate.

## Upload notes

Upload the contents of `site/tiltseven/` to the StackCP web root for `tiltseven.com`, preserving the `assets/` directory.

Do not upload repository-private files, `.git`, environment files, keys, logs, screenshots with private data, or development-only artifacts.

## Smoke test

Before declaring the domain ready:

1. Open `https://tiltseven.com`.
2. Open `https://www.tiltseven.com`.
3. Confirm both present the same TiltSeven page without certificate warnings.
4. Confirm the primary CTA points to `https://casino.tiltseven.com/`.
5. Confirm visible copy says play tokens have no cash value and does not mention deposits, purchases, withdrawals, redemptions, prizes, or transferable value as available features.
6. Test desktop and mobile widths for horizontal overflow.
