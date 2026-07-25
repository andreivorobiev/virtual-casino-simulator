# TiltSeven future publication checklist

Status: repository-only planning material. No publication is authorized by
this file or by the scaffold that contains it.

## Approval boundary

Before any upload or live change, the owner must approve an exact publication
packet naming:

- the canonical public hostname and redirect policy;
- the approved hosting account and destination path;
- DNS and TLS ownership;
- the exact reviewed Git commit and artifact digest;
- privacy, analytics, accessibility, and rollback expectations; and
- the operator authorized to perform and verify the change.

This repository merge does not select those values and must not be read as
permission to alter a provider account, DNS, TLS, billing, public hosting, or
the deployed Casino application.

## Candidate preparation

When a later publication packet is approved:

1. Build an immutable archive from the accepted merge commit.
2. Record the archive digest and the exact file inventory.
3. Confirm the archive contains only the approved static site files.
4. Re-run the governed EN/RU visual matrix against the publication candidate.
5. Verify the Casino link still points to the separately governed canonical
   Casino origin without changing that deployment.

## Safety checks

- Keep the site static: no JavaScript, forms, trackers, payment controls, or
  third-party runtime resources.
- Preserve the play-token/no-cash-value boundary in both locales.
- Do not upload repository metadata, environment files, keys, logs, evidence,
  credentials, or development artifacts.
- Require trusted HTTPS and correct host routing before making a public link
  discoverable.

## Post-publication verification

A future owner-approved operator must independently verify the canonical and
redirect hosts, certificate identity, HSTS behavior, file digest, English and
Russian rendering, keyboard navigation, responsive containment, safety copy,
Casino destination, observability, and rollback. Until that packet exists and
passes, this directory remains an undeployed repository scaffold.
