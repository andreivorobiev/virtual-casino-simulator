# Curated What's New browser tour

Issue #165; requirements TOUR-001, TOUR-002, TOUR-003, TEST-106.

The application consumes the existing self-only What's New API after authenticated routing.
Only a terms-complete registered account can see one merged, capped native dialog. Application
and module version bumps alone never activate it: the release coordinator must explicitly opt
entries into `docs/releases/whats_new.json`. The shipped catalog remains disabled in this change.

The dialog uses existing shell-domain release copy and the installed localization fallback chain.
Missing entry translations reject the complete tour rather than displaying resource keys or
acknowledging unseen content. Copy is rendered through text nodes. Only the fixed GitHub repository
changelog is linked; an unrecognized catalog path is omitted. Terms/privacy changes are separate
consent flows and must never be placed in this tour.

“Got it” sends the existing empty-body acknowledgement and closes after the server confirms
persistence. A failed or unconfirmed response retains a localized error and permits an explicit
retry. “Not now” and Escape only close the current dialog: they make no persistence promise and
the tour can return on the next authenticated entry. No browser storage or identity/version fields
are added. Teardown invalidates pending responses, and another open dialog takes priority.
The public JavaScript view is included in the existing exact service-worker shell allowlist
so its static import cannot break offline bootstrap (PWA-002, TEST-095). Tour API responses and
acknowledgements remain network-only; no private state is added to the offline cache.
During browser integration, duplicate native/synthetic online notifications exposed overlapping
route restores. PWA-002 now coalesces concurrent notifications into one in-flight authoritative
restore. A later explicit attempt remains possible after failure; there is no automatic retry,
timeout increase, or change to server-action gating. A real-module Node regression and the
unchanged BR-PWA-001 reconnect journey cover this prerequisite.

## Validation and evidence

- `API-TOUR-001`: isolated server eligibility/dismissal plus deterministic production-controller
  tests in `tests/unit/whats_new_view.test.mjs` (no browser/listener in the API lane).
- `BR-TOUR-001`: authenticated real Chromium shell, native modal focus containment, EN/RU copy,
  four matrix viewports, reduced motion, unconfirmed save, local deferral, persisted dismissal
  after provider reconstruction, and next-release eligibility.
- The Browser adapter invokes the real `casino.core.whats_new` functions using a disposable JSON
  provider and a test-only catalog. Authentication still uses the ordinary isolated test server;
  tour traffic is page-local fixture traffic, not a production rollout or live-provider claim.
- Matrix surface `whats_new`, plus `shell_lobby/authenticated` and `roulette/betting` after modal removal. The standard
  in `docs/visual_design_standard.md` remains authoritative. Screenshots use
  `logs/test-runs/after-pass-whats-new-<locale>-<viewport>.png` with source/locale/state sidecars.
- Ordinary Browser discovery adds one case to the existing Lobby affinity owner; unmeasured
  duration uses the existing reviewed-profile median until hosted profiling. The tracked duration
  profile, formal allocation, workflow, and timing budgets are unchanged.

Issue #165 remains open until release-copy review, explicit catalog activation, required hosted
checks, and rollout acceptance are complete. No VM, DNS, cloud, provider, schema, signup, OAuth,
gameplay, or ledger changes are part of this continuation.
